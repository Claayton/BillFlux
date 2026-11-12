using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

namespace BillFlux.PrintAgent
{
    /// <summary>
    /// Ícone na bandeja: escolher impressora, papel, iniciar com o Windows,
    /// imprimir teste e sair. Fica invisível para o operador do caixa.
    /// </summary>
    public sealed class TrayApplication : ApplicationContext
    {
        private readonly AgentConfig _config;
        private readonly WebViewPrinter _printer;
        private readonly Control _marshaller;
        private readonly NotifyIcon _tray;
        private readonly ContextMenuStrip _menu;
        private readonly ToolStripMenuItem _printerMenu;
        private readonly ToolStripMenuItem _paperMenu;
        private readonly ToolStripMenuItem _autoStartItem;

        private PrintServer _server;

        public TrayApplication(AgentConfig config)
        {
            _config = config;
            _config.Normalize();

            // Control oculto só para voltar à thread da interface.
            _marshaller = new Control();
            _marshaller.CreateControl();

            _printer = new WebViewPrinter();
            _printer.Start();

            _printerMenu = new ToolStripMenuItem("Impressora");
            _paperMenu = new ToolStripMenuItem("Papel");
            _autoStartItem = new ToolStripMenuItem("Iniciar com o Windows") { CheckOnClick = true };
            _autoStartItem.Click += OnToggleAutoStart;

            _menu = new ContextMenuStrip();
            _menu.Items.Add(new ToolStripMenuItem("BillFlux — Agente de impressão") { Enabled = false });
            _menu.Items.Add(new ToolStripSeparator());
            _menu.Items.Add(_printerMenu);
            _menu.Items.Add(_paperMenu);
            _menu.Items.Add(_autoStartItem);
            _menu.Items.Add(new ToolStripSeparator());
            _menu.Items.Add(new ToolStripMenuItem("Imprimir teste", null, OnPrintTest));
            _menu.Items.Add(new ToolStripMenuItem("Abrir pasta de configuração", null, OnOpenDataFolder));
            _menu.Items.Add(new ToolStripSeparator());
            _menu.Items.Add(new ToolStripMenuItem("Sair", null, OnExit));

            _tray = new NotifyIcon
            {
                Icon = AgentIcon.Create(),
                Text = "BillFlux — Agente de impressão",
                ContextMenuStrip = _menu,
                Visible = true,
            };
            _tray.DoubleClick += OnTrayDoubleClick;

            SyncAutoStart();
            BuildPrinterMenu();
            BuildPaperMenu();
            RefreshChecks();
            StartServer();
        }

        private void StartServer()
        {
            try
            {
                _server = new PrintServer(
                    _config.Port,
                    delegate { return _config; },
                    delegate(PrintJob job) { return _printer.PrintAsync(job); },
                    BuildStatus,
                    OnConfigChangedFromApi
                );
                _server.Start();
                ShowBalloon(
                    "Agente de impressão ativo",
                    "O BillFlux vai imprimir direto, sem diálogo e sem cabeçalho/rodapé."
                );
            }
            catch (Exception ex)
            {
                Log.Error("Não foi possível abrir a porta " + _config.Port, ex);
                ShowBalloon(
                    "Agente de impressão",
                    "Não foi possível iniciar o serviço local (porta "
                        + _config.Port
                        + "). Feche outro agente e abra novamente.",
                    ToolTipIcon.Error
                );
            }
        }

        private Dictionary<string, object> BuildStatus()
        {
            var status = _config.ToStatus();
            status["busy"] = _printer.Busy;
            return status;
        }

        private void OnConfigChangedFromApi()
        {
            Post(delegate
            {
                BuildPrinterMenu();
                BuildPaperMenu();
                RefreshChecks();
            });
        }

        private void Post(Action action)
        {
            try
            {
                if (_marshaller.IsDisposed) return;
                _marshaller.BeginInvoke(action);
            }
            catch
            {
                // encerrando
            }
        }

        private void BuildPrinterMenu()
        {
            _printerMenu.DropDownItems.Clear();

            var defaultItem = new ToolStripMenuItem("Impressora padrão do Windows")
            {
                Tag = string.Empty,
            };
            defaultItem.Click += OnSelectPrinter;
            _printerMenu.DropDownItems.Add(defaultItem);
            _printerMenu.DropDownItems.Add(new ToolStripSeparator());

            var printers = PrinterCatalog.Names();
            if (printers.Length == 0)
            {
                _printerMenu.DropDownItems.Add(
                    new ToolStripMenuItem("Nenhuma impressora encontrada") { Enabled = false }
                );
                return;
            }

            foreach (var name in printers)
            {
                var item = new ToolStripMenuItem(name) { Tag = name };
                item.Click += OnSelectPrinter;
                _printerMenu.DropDownItems.Add(item);
            }
        }

        private void BuildPaperMenu()
        {
            _paperMenu.DropDownItems.Clear();

            var width58 = new ToolStripMenuItem("58 mm") { Tag = 58 };
            width58.Click += OnSelectPaper;
            _paperMenu.DropDownItems.Add(width58);

            var width80 = new ToolStripMenuItem("80 mm") { Tag = 80 };
            width80.Click += OnSelectPaper;
            _paperMenu.DropDownItems.Add(width80);
        }

        private void RefreshChecks()
        {
            foreach (ToolStripItem item in _printerMenu.DropDownItems)
            {
                var menuItem = item as ToolStripMenuItem;
                if (menuItem == null || !(menuItem.Tag is string)) continue;
                menuItem.Checked = string.Equals(
                    (string)menuItem.Tag,
                    _config.Printer ?? string.Empty,
                    StringComparison.OrdinalIgnoreCase
                );
            }

            foreach (ToolStripItem item in _paperMenu.DropDownItems)
            {
                var menuItem = item as ToolStripMenuItem;
                if (menuItem == null || !(menuItem.Tag is int)) continue;
                menuItem.Checked = (int)menuItem.Tag == _config.WidthMm;
            }

            _autoStartItem.Checked = _config.AutoStart;
            _tray.Text = BuildTrayText();
        }

        private string BuildTrayText()
        {
            var printer = string.IsNullOrWhiteSpace(_config.Printer)
                ? "padrão do Windows"
                : _config.Printer;
            var text = "BillFlux — " + printer + " (" + _config.WidthMm + " mm)";
            // NotifyIcon.Text aceita no máximo 63 caracteres.
            return text.Length <= 63 ? text : text.Substring(0, 60) + "...";
        }

        private void OnSelectPrinter(object sender, EventArgs e)
        {
            var item = sender as ToolStripMenuItem;
            if (item == null) return;

            _config.Printer = (string)item.Tag ?? string.Empty;
            _config.Save();
            RefreshChecks();
            ShowBalloon(
                "Impressora do BillFlux",
                string.IsNullOrWhiteSpace(_config.Printer)
                    ? "Usando a impressora padrão do Windows."
                    : "Agora imprimindo em: " + _config.Printer
            );
        }

        private void OnSelectPaper(object sender, EventArgs e)
        {
            var item = sender as ToolStripMenuItem;
            if (item == null || !(item.Tag is int)) return;

            _config.WidthMm = (int)item.Tag;
            _config.Save();
            RefreshChecks();
        }

        private void OnToggleAutoStart(object sender, EventArgs e)
        {
            _config.AutoStart = _autoStartItem.Checked;
            AutoStartManager.SetEnabled(_config.AutoStart);
            _config.Save();
            RefreshChecks();
        }

        private void SyncAutoStart()
        {
            var enabled = AutoStartManager.IsEnabled();
            if (enabled != _config.AutoStart)
            {
                _config.AutoStart = enabled;
                _config.Save();
            }
            else if (enabled)
            {
                // Reaplica o caminho: o usuário pode ter movido a pasta do agente.
                AutoStartManager.SetEnabled(true);
            }
        }

        private async void OnPrintTest(object sender, EventArgs e)
        {
            var printer = string.IsNullOrWhiteSpace(_config.Printer)
                ? "Impressora padrão do Windows"
                : _config.Printer;

            var html =
                "<div style=\"font-family:Arial,Helvetica,sans-serif;padding:6px\">"
                + "<div style=\"text-align:center;font-size:15px;font-weight:bold\">BillFlux</div>"
                + "<div style=\"text-align:center;font-size:11px;margin-bottom:6px\">Teste de impressão</div>"
                + "<div style=\"border-top:1px dashed #000;margin:6px 0\"></div>"
                + "<div style=\"font-size:11px;line-height:1.5\">"
                + "Agente de impressão funcionando.<br>"
                + "Impressora: "
                + Escape(printer)
                + "<br>Papel: "
                + _config.WidthMm
                + " mm<br>Data: "
                + Escape(DateTime.Now.ToString("dd/MM/yyyy HH:mm"))
                + "</div>"
                + "<div style=\"border-top:1px dashed #000;margin:6px 0\"></div>"
                + "<div style=\"text-align:center;font-size:10px\">Sem diálogo, sem cabeçalho e sem rodapé.</div>"
                + "</div>";

            var job = new PrintJob
            {
                BodyHtml = html,
                Css = string.Empty,
                WidthMm = _config.WidthMm,
                HeightMm = 70,
                Printer = _config.Printer,
            };

            ShowBalloon("BillFlux", "Enviando a impressão de teste…");
            var result = await _printer.PrintAsync(job);
            if (result.Ok)
            {
                ShowBalloon("Impressão de teste enviada", "Confira a bobina da impressora.");
            }
            else
            {
                ShowBalloon("Falha no teste", result.Error, ToolTipIcon.Error);
            }
        }

        private void OnOpenDataFolder(object sender, EventArgs e)
        {
            try
            {
                Directory.CreateDirectory(AgentConfig.Folder);
                Process.Start("explorer.exe", "\"" + AgentConfig.Folder + "\"");
            }
            catch (Exception ex)
            {
                Log.Error("Não foi possível abrir a pasta de configuração", ex);
            }
        }

        private void OnTrayDoubleClick(object sender, EventArgs e)
        {
            var printer = string.IsNullOrWhiteSpace(_config.Printer)
                ? "padrão do Windows"
                : _config.Printer;
            ShowBalloon(
                "BillFlux — Agente de impressão",
                "Impressora: " + printer + "\nPapel: " + _config.WidthMm + " mm"
            );
        }

        private void OnExit(object sender, EventArgs e)
        {
            ExitThread();
        }

        private void ShowBalloon(string title, string text)
        {
            ShowBalloon(title, text, ToolTipIcon.Info);
        }

        private void ShowBalloon(string title, string text, ToolTipIcon icon)
        {
            try
            {
                _tray.ShowBalloonTip(4000, title, text, icon);
            }
            catch
            {
                // bandeja indisponível
            }
        }

        private static string Escape(string value)
        {
            return (value ?? string.Empty)
                .Replace("&", "&amp;")
                .Replace("<", "&lt;")
                .Replace(">", "&gt;");
        }

        protected override void Dispose(bool disposing)
        {
            if (disposing)
            {
                if (_server != null) _server.Dispose();
                _printer.Dispose();

                _tray.Visible = false;
                _tray.Dispose();
                _menu.Dispose();

                if (!_marshaller.IsDisposed) _marshaller.Dispose();
            }
            base.Dispose(disposing);
        }
    }
}
