using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading.Tasks;
using System.Web.Script.Serialization;

namespace BillFlux.PrintAgent
{
    /// <summary>
    /// Servidor HTTP mínimo em 127.0.0.1 (TcpListener, sem URL ACL).
    ///
    /// Endpoints:
    ///   GET  /status    → estado, impressora e papel configurados
    ///   GET  /printers  → impressoras instaladas no Windows
    ///   GET  /config    → configuração atual
    ///   POST /config    → altera impressora/papel
    ///   POST /print     → { bodyHtml, css, widthMm, heightMm, printer }
    /// </summary>
    public sealed class PrintServer : IDisposable
    {
        private readonly TcpListener _listener;
        private readonly Func<AgentConfig> _config;
        private readonly Func<PrintJob, Task<PrintResult>> _print;
        private readonly Func<Dictionary<string, object>> _status;
        private readonly Action _onConfigChanged;
        private readonly JavaScriptSerializer _json = new JavaScriptSerializer
        {
            MaxJsonLength = int.MaxValue,
        };

        private volatile bool _running;

        public PrintServer(
            int port,
            Func<AgentConfig> config,
            Func<PrintJob, Task<PrintResult>> print,
            Func<Dictionary<string, object>> status,
            Action onConfigChanged
        )
        {
            _config = config;
            _print = print;
            _status = status;
            _onConfigChanged = onConfigChanged;
            _listener = new TcpListener(IPAddress.Loopback, port);
        }

        public void Start()
        {
            _listener.Start();
            _running = true;
            var ignored = AcceptLoopAsync();
            Log.Info("Servidor local ouvindo em http://127.0.0.1:" + ((IPEndPoint)_listener.LocalEndpoint).Port);
        }

        private async Task AcceptLoopAsync()
        {
            while (_running)
            {
                TcpClient client;
                try
                {
                    client = await _listener.AcceptTcpClientAsync().ConfigureAwait(false);
                }
                catch (ObjectDisposedException)
                {
                    break;
                }
                catch (SocketException)
                {
                    break;
                }
                catch (Exception ex)
                {
                    Log.Error("Falha ao aceitar conexão", ex);
                    break;
                }

                var ignored = HandleClientAsync(client);
            }
        }

        private async Task HandleClientAsync(TcpClient client)
        {
            using (client)
            {
                try
                {
                    client.NoDelay = true;
                    var stream = client.GetStream();
                    var request = await ReadRequestAsync(stream).ConfigureAwait(false);
                    if (request == null) return;

                    int code;
                    string contentType;
                    string body;

                    if (request.Method == "OPTIONS")
                    {
                        code = 204;
                        contentType = "text/plain; charset=utf-8";
                        body = string.Empty;
                    }
                    else
                    {
                        contentType = "application/json; charset=utf-8";
                        body = Route(request, out code);
                    }

                    await WriteResponseAsync(stream, code, contentType, body).ConfigureAwait(false);
                }
                catch (IOException)
                {
                    // cliente desconectou no meio: normal
                }
                catch (Exception ex)
                {
                    Log.Error("Falha ao atender uma requisição", ex);
                }
            }
        }

        private string Route(HttpRequest request, out int code)
        {
            try
            {
                switch (request.Path)
                {
                    case "/status":
                        return Status(out code);

                    case "/printers":
                        code = 200;
                        return _json.Serialize(
                            new Dictionary<string, object>
                            {
                                { "ok", true },
                                { "printers", PrinterCatalog.Names() },
                            }
                        );

                    case "/config":
                        if (request.Method == "POST") return UpdateConfig(request, out code);
                        return Config(out code);

                    case "/print":
                        if (request.Method != "POST")
                        {
                            code = 405;
                            return Error("Use POST para imprimir.");
                        }
                        return Print(request, out code);

                    case "/":
                        code = 200;
                        return _json.Serialize(
                            new Dictionary<string, object>
                            {
                                { "ok", true },
                                { "name", "BillFlux Print Agent" },
                                { "version", AgentConfig.Version },
                            }
                        );

                    default:
                        code = 404;
                        return Error("Endpoint não encontrado.");
                }
            }
            catch (Exception ex)
            {
                Log.Error("Erro na rota " + request.Path, ex);
                code = 500;
                return Error(ex.GetBaseException().Message);
            }
        }

        private string Status(out int code)
        {
            code = 200;
            var data = _status == null
                ? new Dictionary<string, object>()
                : _status();
            data["ok"] = true;
            data["name"] = "BillFlux Print Agent";
            data["version"] = AgentConfig.Version;
            data["printers"] = PrinterCatalog.Names();
            return _json.Serialize(data);
        }

        private string Config(out int code)
        {
            code = 200;
            var data = _config().ToStatus();
            data["ok"] = true;
            return _json.Serialize(data);
        }

        private string UpdateConfig(HttpRequest request, out int code)
        {
            var payload = ParseBody(request.Body);
            if (payload == null)
            {
                code = 400;
                return Error("JSON inválido.");
            }

            var config = _config();
            var printer = GetString(payload, "printer");
            if (!string.IsNullOrWhiteSpace(printer))
            {
                config.Printer = printer.Trim();
            }

            var width = GetInt(payload, "widthMm", config.WidthMm);
            if (width == 58 || width == 80) config.WidthMm = width;

            config.Save();
            if (_onConfigChanged != null) _onConfigChanged();

            code = 200;
            var data = config.ToStatus();
            data["ok"] = true;
            return _json.Serialize(data);
        }

        private string Print(HttpRequest request, out int code)
        {
            var payload = ParseBody(request.Body);
            if (payload == null)
            {
                code = 400;
                return Error("JSON inválido.");
            }

            var html = GetString(payload, "html");
            var bodyHtml = GetString(payload, "bodyHtml");
            if (string.IsNullOrWhiteSpace(html) && string.IsNullOrWhiteSpace(bodyHtml))
            {
                code = 400;
                return Error("Envie o HTML do cupom em 'bodyHtml' (ou 'html').");
            }

            var config = _config();
            var width = GetInt(payload, "widthMm", config.WidthMm);
            if (width < 40 || width > 120) width = config.WidthMm;

            var height = GetInt(payload, "heightMm", width);
            if (height < width) height = width;
            if (height > 1000) height = 1000;

            var printer = GetString(payload, "printer");
            if (string.IsNullOrWhiteSpace(printer)) printer = config.Printer;
            if (!string.IsNullOrWhiteSpace(printer) && !PrinterCatalog.Exists(printer))
            {
                // Impressora removida/renomeada: cai na padrão do Windows em vez
                // de falhar a venda no caixa.
                Log.Info("Impressora configurada não existe mais; usando a padrão: " + printer);
                printer = string.Empty;
            }

            var job = new PrintJob
            {
                Html = html,
                BodyHtml = bodyHtml,
                Css = GetString(payload, "css"),
                Links = GetStringArray(payload, "links"),
                WidthMm = width,
                HeightMm = height,
                Printer = printer,
            };

            var result = _print(job).GetAwaiter().GetResult();
            var response = new Dictionary<string, object>
            {
                { "ok", result.Ok },
                { "status", result.Status },
            };
            if (!string.IsNullOrEmpty(result.Error)) response["error"] = result.Error;

            if (result.Ok)
            {
                code = 200;
                Log.Info("Impressão enviada: " + width + "mm x " + height + "mm em '" + printer + "'.");
            }
            else
            {
                code = 500;
                Log.Error("Impressão falhou: " + result.Error, null);
            }
            return _json.Serialize(response);
        }

        private Dictionary<string, object> ParseBody(string body)
        {
            if (string.IsNullOrWhiteSpace(body)) return null;
            try
            {
                return _json.Deserialize<Dictionary<string, object>>(body);
            }
            catch (Exception ex)
            {
                Log.Error("JSON inválido", ex);
                return null;
            }
        }

        private string Error(string message)
        {
            return _json.Serialize(
                new Dictionary<string, object> { { "ok", false }, { "error", message } }
            );
        }

        private static string GetString(Dictionary<string, object> data, string key)
        {
            object value;
            if (data != null && data.TryGetValue(key, out value) && value != null)
            {
                return Convert.ToString(value, CultureInfo.InvariantCulture);
            }
            return null;
        }

        private static int GetInt(Dictionary<string, object> data, string key, int fallback)
        {
            var text = GetString(data, key);
            int value;
            return int.TryParse(text, NumberStyles.Integer, CultureInfo.InvariantCulture, out value)
                ? value
                : fallback;
        }

        private static string[] GetStringArray(Dictionary<string, object> data, string key)
        {
            object value;
            if (data == null || !data.TryGetValue(key, out value) || value == null)
            {
                return new string[0];
            }
            if (value is string) return new string[0];

            var items = value as System.Collections.IEnumerable;
            if (items == null) return new string[0];

            var result = new List<string>();
            foreach (var item in items)
            {
                var text = Convert.ToString(item, CultureInfo.InvariantCulture);
                if (!string.IsNullOrWhiteSpace(text)) result.Add(text);
            }
            return result.ToArray();
        }

        private static async Task<HttpRequest> ReadRequestAsync(NetworkStream stream)
        {
            var buffer = new MemoryStream();
            var chunk = new byte[4096];
            var headerEnd = -1;

            while (headerEnd < 0)
            {
                var read = await stream.ReadAsync(chunk, 0, chunk.Length).ConfigureAwait(false);
                if (read <= 0) return null;
                buffer.Write(chunk, 0, read);
                headerEnd = FindHeaderEnd(buffer.GetBuffer(), (int)buffer.Length);
                if (buffer.Length > 128 * 1024) return null;
            }

            var all = buffer.ToArray();
            var headerText = Encoding.ASCII.GetString(all, 0, headerEnd);
            var lines = headerText.Split(new[] { "\r\n" }, StringSplitOptions.None);
            var requestLine = lines[0].Split(' ');
            if (requestLine.Length < 2) return null;

            var headers = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            for (var i = 1; i < lines.Length; i++)
            {
                var index = lines[i].IndexOf(':');
                if (index <= 0) continue;
                headers[lines[i].Substring(0, index).Trim()] = lines[i].Substring(index + 1).Trim();
            }

            var contentLength = 0;
            string lengthHeader;
            if (headers.TryGetValue("Content-Length", out lengthHeader))
            {
                int.TryParse(lengthHeader, NumberStyles.Integer, CultureInfo.InvariantCulture, out contentLength);
            }
            if (contentLength < 0) contentLength = 0;
            if (contentLength > 32 * 1024 * 1024) return null;

            var bodyBytes = new byte[contentLength];
            var alreadyRead = Math.Min(all.Length - (headerEnd + 4), contentLength);
            if (alreadyRead > 0)
            {
                Array.Copy(all, headerEnd + 4, bodyBytes, 0, alreadyRead);
            }

            var offset = alreadyRead;
            while (offset < contentLength)
            {
                var read = await stream.ReadAsync(bodyBytes, offset, contentLength - offset).ConfigureAwait(false);
                if (read <= 0) break;
                offset += read;
            }

            return new HttpRequest
            {
                Method = requestLine[0].ToUpperInvariant(),
                Path = requestLine[1].Split('?')[0],
                Headers = headers,
                Body = Encoding.UTF8.GetString(bodyBytes, 0, offset),
            };
        }

        private static int FindHeaderEnd(byte[] buffer, int length)
        {
            for (var i = 0; i + 3 < length; i++)
            {
                if (
                    buffer[i] == 13
                    && buffer[i + 1] == 10
                    && buffer[i + 2] == 13
                    && buffer[i + 3] == 10
                )
                {
                    return i;
                }
            }
            return -1;
        }

        private static async Task WriteResponseAsync(
            NetworkStream stream,
            int statusCode,
            string contentType,
            string body
        )
        {
            var bytes = Encoding.UTF8.GetBytes(body ?? string.Empty);
            var reason = statusCode == 200
                ? "OK"
                : statusCode == 204
                    ? "No Content"
                    : statusCode == 400
                        ? "Bad Request"
                        : statusCode == 404
                            ? "Not Found"
                            : statusCode == 405
                                ? "Method Not Allowed"
                                : "Internal Server Error";

            var header = new StringBuilder();
            header.Append("HTTP/1.1 ").Append(statusCode).Append(' ').Append(reason).Append("\r\n");
            header.Append("Content-Type: ").Append(contentType).Append("\r\n");
            header.Append("Content-Length: ").Append(bytes.Length).Append("\r\n");
            header.Append("Cache-Control: no-store\r\n");
            header.Append("Connection: close\r\n");
            header.Append("Access-Control-Allow-Origin: *\r\n");
            header.Append("Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n");
            header.Append("Access-Control-Allow-Headers: Content-Type\r\n");
            // Chrome bloqueia página pública chamando 127.0.0.1 sem isso.
            header.Append("Access-Control-Allow-Private-Network: true\r\n");
            header.Append("\r\n");

            var headerBytes = Encoding.ASCII.GetBytes(header.ToString());
            await stream.WriteAsync(headerBytes, 0, headerBytes.Length).ConfigureAwait(false);
            if (bytes.Length > 0)
            {
                await stream.WriteAsync(bytes, 0, bytes.Length).ConfigureAwait(false);
            }
            await stream.FlushAsync().ConfigureAwait(false);
        }

        public void Dispose()
        {
            _running = false;
            try
            {
                _listener.Stop();
            }
            catch
            {
                // já parado
            }
        }

        private sealed class HttpRequest
        {
            public string Method;
            public string Path;
            public Dictionary<string, string> Headers;
            public string Body;
        }
    }
}
