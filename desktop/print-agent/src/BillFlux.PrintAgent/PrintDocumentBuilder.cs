using System;
using System.Globalization;
using System.Text;

namespace BillFlux.PrintAgent
{
    /// <summary>
    /// Monta o documento final que o WebView2 renderiza.
    ///
    /// O navegador manda só o corpo (cupom/DANFE) + CSS; aqui entram as regras
    /// de página que garantem papel do tamanho certo, margem zero e nada de
    /// cabeçalho/rodapé.
    /// </summary>
    internal static class PrintDocumentBuilder
    {
        public static string Build(PrintJob job, int widthMm, int heightMm)
        {
            if (!string.IsNullOrWhiteSpace(job.Html))
            {
                return job.Html;
            }

            var body = job.BodyHtml ?? string.Empty;
            var css = job.Css ?? string.Empty;

            var builder = new StringBuilder();
            builder.Append("<!doctype html><html lang=\"pt-BR\"><head><meta charset=\"utf-8\">");
            builder.Append("<meta name=\"color-scheme\" content=\"light\">");
            builder.Append("<title>BillFlux</title>");

            if (job.Links != null)
            {
                foreach (var link in job.Links)
                {
                    if (string.IsNullOrWhiteSpace(link)) continue;
                    builder.Append("<link rel=\"stylesheet\" href=\"");
                    builder.Append(EscapeHtml(link.Trim()));
                    builder.Append("\">");
                }
            }

            // CSS da aplicação primeiro; as regras de página vêm depois para
            // vencerem as regras de impressão do app (mesma especificidade).
            builder.Append("<style>");
            builder.Append(css);
            builder.Append("</style>");

            builder.Append("<style>");
            builder.Append(BuildPageCss(widthMm, heightMm));
            builder.Append("</style>");
            builder.Append("</head><body>");
            builder.Append(body);
            builder.Append("</body></html>");
            return builder.ToString();
        }

        private static string BuildPageCss(int widthMm, int heightMm)
        {
            return string.Format(
                CultureInfo.InvariantCulture,
                @"
@page {{ size: {0}mm {1}mm; margin: 0; }}
html, body {{
  margin: 0 !important;
  padding: 0 !important;
  background: #fff !important;
}}
body {{
  width: {0}mm !important;
  min-width: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  color: #000;
  visibility: visible !important;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}}
body > * {{
  position: static !important;
  box-sizing: border-box !important;
  width: {0}mm !important;
  max-width: {0}mm !important;
  margin: 0 !important;
  visibility: visible !important;
}}
@media print {{
  html, body {{ margin: 0 !important; padding: 0 !important; visibility: visible !important; }}
  body > * {{ display: block !important; visibility: visible !important; }}
}}
",
                widthMm,
                heightMm
            );
        }

        private static string EscapeHtml(string value)
        {
            return value
                .Replace("&", "&amp;")
                .Replace("\"", "&quot;")
                .Replace("<", "&lt;")
                .Replace(">", "&gt;");
        }
    }
}
