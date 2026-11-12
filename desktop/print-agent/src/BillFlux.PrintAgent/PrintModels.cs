using System;

namespace BillFlux.PrintAgent
{
    /// <summary>Um trabalho de impressão recebido do BillFlux.</summary>
    public sealed class PrintJob
    {
        /// <summary>HTML completo do documento (opcional; o servidor também monta).</summary>
        public string Html { get; set; }

        /// <summary>Corpo do documento (o caso normal vindo do navegador).</summary>
        public string BodyHtml { get; set; }

        /// <summary>CSS da aplicação (cupom/DANFE).</summary>
        public string Css { get; set; }

        /// <summary>Folhas externas que o documento deve carregar.</summary>
        public string[] Links { get; set; }

        public int WidthMm { get; set; }
        public int HeightMm { get; set; }

        /// <summary>Impressora escolhida; vazio usa a configuração/padrão do Windows.</summary>
        public string Printer { get; set; }
    }

    /// <summary>Resultado de uma impressão.</summary>
    public sealed class PrintResult
    {
        public bool Ok { get; set; }
        public string Status { get; set; }
        public string Error { get; set; }

        public static PrintResult Success(string status)
        {
            return new PrintResult { Ok = true, Status = status ?? "Succeeded" };
        }

        public static PrintResult Failure(string error)
        {
            return new PrintResult { Ok = false, Status = "Error", Error = error };
        }
    }
}
