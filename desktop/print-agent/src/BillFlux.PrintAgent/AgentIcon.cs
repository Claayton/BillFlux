using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Text;

namespace BillFlux.PrintAgent
{
    /// <summary>
    /// Ícone da bandeja desenhado em memória (evita arquivo .ico no build):
    /// círculo azul com a letra B, no estilo do BillFlux.
    /// </summary>
    internal static class AgentIcon
    {
        private static Icon _cached;
        private static IntPtr _handle;

        public static Icon Create()
        {
            if (_cached != null) return _cached;

            using (var bitmap = new Bitmap(32, 32))
            {
                using (var graphics = Graphics.FromImage(bitmap))
                {
                    graphics.SmoothingMode = SmoothingMode.AntiAlias;
                    graphics.TextRenderingHint = TextRenderingHint.AntiAliasGridFit;
                    graphics.Clear(Color.Transparent);

                    using (var background = new SolidBrush(Color.FromArgb(37, 99, 235)))
                    {
                        graphics.FillEllipse(background, 0, 0, 31, 31);
                    }

                    using (var font = new Font("Segoe UI", 18f, FontStyle.Bold, GraphicsUnit.Pixel))
                    using (var text = new SolidBrush(Color.White))
                    using (var format = new StringFormat())
                    {
                        format.Alignment = StringAlignment.Center;
                        format.LineAlignment = StringAlignment.Center;
                        graphics.DrawString("B", font, text, new RectangleF(0, 0, 32, 32), format);
                    }
                }

                _handle = bitmap.GetHicon();
                _cached = Icon.FromHandle(_handle);
            }

            return _cached;
        }
    }
}
