using System;
using System.Drawing;
using System.Globalization;
using System.IO;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

namespace BillFlux.PrintAgent
{
    /// <summary>
    /// Renderiza o HTML num WebView2 invisível e imprime direto na impressora
    /// escolhida, sem diálogo e sem cabeçalho/rodapé do navegador.
    ///
    /// O WebView2 roda numa thread STA própria, com um formulário fora da tela.
    /// Assim a bandeja (outra thread) nunca trava esperando a impressão.
    /// </summary>
    public sealed class WebViewPrinter : IDisposable
    {
        private const double MmPerInch = 25.4;
        private const int PageTimeoutMs = 20000;
        private const int ImageTimeoutMs = 5000;

        private readonly string _userDataFolder;
        private readonly string _tempFolder;
        private readonly TaskCompletionSource<bool> _ready =
            new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
        private readonly SemaphoreSlim _printLock = new SemaphoreSlim(1, 1);

        private Form _host;
        private WebView2 _webView;
        private Thread _thread;
        private volatile bool _disposed;
        private volatile bool _busy;

        public WebViewPrinter()
        {
            var local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            _userDataFolder = Path.Combine(local, "BillFlux", "WebView2");
            _tempFolder = Path.Combine(Path.GetTempPath(), "BillFluxPrint");
        }

        public bool Busy
        {
            get { return _busy; }
        }

        public void Start()
        {
            _thread = new Thread(RunMessageLoop);
            _thread.IsBackground = true;
            _thread.Name = "BillFlux WebView2";
            _thread.SetApartmentState(ApartmentState.STA);
            _thread.Start();
        }

        private void RunMessageLoop()
        {
            try
            {
                Directory.CreateDirectory(_userDataFolder);
                Directory.CreateDirectory(_tempFolder);
                CleanupTempFiles();
            }
            catch (Exception ex)
            {
                Log.Error("Não foi possível preparar as pastas do WebView2", ex);
            }

            _host = new Form
            {
                Text = "BillFlux — Agente de impressão",
                ShowInTaskbar = false,
                FormBorderStyle = FormBorderStyle.None,
                StartPosition = FormStartPosition.Manual,
                Location = new Point(-32000, -32000),
                Size = new Size(480, 640),
                BackColor = Color.White,
            };

            _host.Load += async delegate { await InitializeAsync(); };
            _host.Shown += delegate
            {
                // Fora da tela, mas tecnicamente visível: o WebView2 precisa
                // renderizar para o PrintAsync funcionar.
                _host.Location = new Point(-32000, -32000);
            };

            try
            {
                Application.Run(_host);
            }
            catch (Exception ex)
            {
                Log.Error("Falha no formulário do WebView2", ex);
                _ready.TrySetException(ex);
            }
        }

        private async Task InitializeAsync()
        {
            try
            {
                var environment = await CoreWebView2Environment.CreateAsync(
                    null,
                    _userDataFolder,
                    null
                );

                _webView = new WebView2
                {
                    Dock = DockStyle.Fill,
                    DefaultBackgroundColor = Color.White,
                };
                _host.Controls.Add(_webView);
                await _webView.EnsureCoreWebView2Async(environment);

                var core = _webView.CoreWebView2;
                core.Settings.AreDefaultContextMenusEnabled = false;
                core.Settings.AreDevToolsEnabled = false;
                core.Settings.IsStatusBarEnabled = false;
                core.Settings.AreBrowserAcceleratorKeysEnabled = false;
                core.Settings.IsZoomControlEnabled = false;

                Log.Info("WebView2 pronto.");
                _ready.TrySetResult(true);
            }
            catch (Exception ex)
            {
                Log.Error("Não foi possível iniciar o WebView2", ex);
                _ready.TrySetException(ex);
            }
        }

        /// <summary>Imprime o job e devolve o resultado. Nunca lança.</summary>
        public async Task<PrintResult> PrintAsync(PrintJob job)
        {
            // Um job por vez: o WebView2 é uma página só.
            await _printLock.WaitAsync().ConfigureAwait(false);
            try
            {
                return await PrintCoreAsync(job).ConfigureAwait(false);
            }
            catch (Exception ex)
            {
                Log.Error("Erro inesperado ao imprimir", ex);
                return PrintResult.Failure(ex.GetBaseException().Message);
            }
            finally
            {
                _printLock.Release();
            }
        }

        private async Task<PrintResult> PrintCoreAsync(PrintJob job)
        {
            if (_disposed) return PrintResult.Failure("O agente está encerrando.");

            var readyTask = await Task.WhenAny(_ready.Task, Task.Delay(PageTimeoutMs));
            if (readyTask != _ready.Task)
            {
                return PrintResult.Failure(
                    "O WebView2 ainda não iniciou. Feche e abra o agente novamente."
                );
            }
            if (_ready.Task.IsFaulted)
            {
                var reason = _ready.Task.Exception == null
                    ? "erro desconhecido"
                    : _ready.Task.Exception.GetBaseException().Message;
                return PrintResult.Failure(
                    "WebView2 indisponível: " + reason + ". Instale o WebView2 Runtime da Microsoft."
                );
            }

            var tcs = new TaskCompletionSource<PrintResult>(
                TaskCreationOptions.RunContinuationsAsynchronously
            );

            try
            {
                _host.BeginInvoke(
                    new Action(
                        async delegate
                        {
                            try
                            {
                                var result = await PrintOnUiThreadAsync(job);
                                tcs.TrySetResult(result);
                            }
                            catch (Exception ex)
                            {
                                Log.Error("Erro ao imprimir", ex);
                                tcs.TrySetResult(PrintResult.Failure(ex.GetBaseException().Message));
                            }
                        }
                    )
                );
            }
            catch (Exception ex)
            {
                return PrintResult.Failure("Não foi possível acionar o WebView2: " + ex.Message);
            }

            return await tcs.Task.ConfigureAwait(false);
        }

        private async Task<PrintResult> PrintOnUiThreadAsync(PrintJob job)
        {
            if (_webView == null || _webView.CoreWebView2 == null)
            {
                return PrintResult.Failure("WebView2 não está pronto.");
            }

            _busy = true;
            var core = _webView.CoreWebView2;
            var widthMm = job.WidthMm <= 0 ? 80 : job.WidthMm;
            var heightMm = job.HeightMm <= 0 ? widthMm : job.HeightMm;

            string tempFile = null;
            try
            {
                var html = PrintDocumentBuilder.Build(job, widthMm, heightMm);
                tempFile = Path.Combine(_tempFolder, "job-" + Guid.NewGuid().ToString("N") + ".html");
                File.WriteAllText(tempFile, html, new UTF8Encoding(false));

                var navigation = new TaskCompletionSource<bool>(
                    TaskCreationOptions.RunContinuationsAsynchronously
                );
                EventHandler<CoreWebView2NavigationCompletedEventArgs> handler = null;
                handler = delegate(object sender, CoreWebView2NavigationCompletedEventArgs args)
                {
                    core.NavigationCompleted -= handler;
                    navigation.TrySetResult(args.IsSuccess);
                };
                core.NavigationCompleted += handler;

                core.Navigate(new Uri(tempFile).AbsoluteUri);

                var finished = await Task.WhenAny(navigation.Task, Task.Delay(PageTimeoutMs));
                if (finished != navigation.Task)
                {
                    return PrintResult.Failure("O documento demorou demais para carregar.");
                }
                if (!await navigation.Task)
                {
                    return PrintResult.Failure("Não foi possível carregar o cupom para impressão.");
                }

                await WaitForPageAsync(core);

                // Mede o conteúdo já renderizado dentro do WebView2: é a altura
                // que o spooler realmente precisa, sem depender da medição do
                // navegador (que pode divergir do CSS final).
                var measuredMm = await MeasureContentHeightMmAsync(core);
                if (measuredMm > 0)
                {
                    heightMm = Math.Min(1000, measuredMm + 2);
                }

                var settings = core.Environment.CreatePrintSettings();
                settings.PrinterName = string.IsNullOrWhiteSpace(job.Printer)
                    ? string.Empty
                    : job.Printer.Trim();
                settings.ShouldPrintHeaderAndFooter = false;
                settings.ShouldPrintBackgrounds = true;
                settings.Orientation = CoreWebView2PrintOrientation.Portrait;
                settings.PageWidth = widthMm / MmPerInch;
                settings.PageHeight = heightMm / MmPerInch;
                settings.MarginTop = 0;
                settings.MarginBottom = 0;
                settings.MarginLeft = 0;
                settings.MarginRight = 0;
                settings.ScaleFactor = 1.0;

                var status = await core.PrintAsync(settings);
                if (status == CoreWebView2PrintStatus.Succeeded)
                {
                    return PrintResult.Success(status.ToString());
                }
                if (status == CoreWebView2PrintStatus.PrinterUnavailable)
                {
                    return PrintResult.Failure(
                        "Impressora indisponível. Confira se ela está ligada e escolhida no agente."
                    );
                }
                return PrintResult.Failure("O Windows não conseguiu imprimir (" + status + ").");
            }
            finally
            {
                _busy = false;
                if (tempFile != null)
                {
                    try
                    {
                        File.Delete(tempFile);
                    }
                    catch
                    {
                        // arquivo temporário: pode ficar para a limpeza inicial
                    }
                }
            }
        }

        /// <summary>Altura real do conteúdo renderizado (px CSS → mm), ou 0.</summary>
        private static async Task<int> MeasureContentHeightMmAsync(CoreWebView2 core)
        {
            const string script =
                "(function(){"
                + "  var body = document.body;"
                + "  if (!body) return 0;"
                + "  var rect = body.getBoundingClientRect ? body.getBoundingClientRect().height : 0;"
                + "  var scroll = body.scrollHeight || 0;"
                + "  return Math.ceil(Math.max(rect, scroll));"
                + "})();";

            try
            {
                var raw = await core.ExecuteScriptAsync(script);
                if (
                    int.TryParse(
                        raw,
                        NumberStyles.Integer,
                        CultureInfo.InvariantCulture,
                        out var px
                    )
                    && px > 0
                )
                {
                    return (int)Math.Ceiling(px * 25.4 / 96.0);
                }
            }
            catch
            {
                // medição é otimização: segue com a altura informada pelo app
            }
            return 0;
        }

        /// <summary>Espera imagens (QR Code) e fontes antes de mandar pro spooler.</summary>
        private static async Task WaitForPageAsync(CoreWebView2 core)
        {
            const string script =
                "(function(){"
                + "  if (document.readyState !== 'complete') return false;"
                + "  var fontsReady = !document.fonts || document.fonts.status === 'loaded';"
                + "  var imagesReady = Array.prototype.every.call(document.images, function(img){"
                + "    return img.complete;"
                + "  });"
                + "  return fontsReady && imagesReady;"
                + "})();";

            var deadline = DateTime.UtcNow.AddMilliseconds(ImageTimeoutMs);
            while (DateTime.UtcNow < deadline)
            {
                try
                {
                    var value = await core.ExecuteScriptAsync(script);
                    if (string.Equals(value, "true", StringComparison.OrdinalIgnoreCase)) return;
                }
                catch
                {
                    // página ainda navegando: tenta de novo
                }
                await Task.Delay(100);
            }
        }

        private void CleanupTempFiles()
        {
            try
            {
                foreach (var file in Directory.GetFiles(_tempFolder, "job-*.html"))
                {
                    try
                    {
                        if (File.GetLastWriteTimeUtc(file) < DateTime.UtcNow.AddHours(-1))
                        {
                            File.Delete(file);
                        }
                    }
                    catch
                    {
                        // ignora arquivo em uso
                    }
                }
            }
            catch
            {
                // pasta temporária indisponível: segue o jogo
            }
        }

        public void Dispose()
        {
            if (_disposed) return;
            _disposed = true;

            try
            {
                if (_host != null && _host.IsHandleCreated)
                {
                    _host.BeginInvoke(new Action(delegate { _host.Close(); }));
                }
            }
            catch
            {
                // thread já encerrada
            }

            try
            {
                if (_thread != null) _thread.Join(3000);
            }
            catch
            {
                // não bloqueia o encerramento
            }
        }
    }
}
