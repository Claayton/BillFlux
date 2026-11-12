using System;
using System.Threading;
using System.Windows.Forms;

namespace BillFlux.PrintAgent
{
    internal static class Program
    {
        /// <summary>Mutex local: impede duas instâncias disputando a mesma porta.</summary>
        private const string MutexName = "BillFlux.PrintAgent.SingleInstance";

        [STAThread]
        private static void Main()
        {
            bool created;
            using (var mutex = new Mutex(true, MutexName, out created))
            {
                if (!created)
                {
                    // Já existe um agente na bandeja: não duplica.
                    return;
                }

                Application.EnableVisualStyles();
                Application.SetCompatibleTextRenderingDefault(false);

                var config = AgentConfig.Load();
                Log.Info("Agente iniciado (versão " + AgentConfig.Version + ").");

                try
                {
                    using (var context = new TrayApplication(config))
                    {
                        Application.Run(context);
                    }
                }
                catch (Exception ex)
                {
                    Log.Error("Falha fatal", ex);
                    MessageBox.Show(
                        "O agente de impressão encerrou por um erro:\r\n\r\n" + ex.Message,
                        "BillFlux — Agente de impressão",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Error
                    );
                }

                Log.Info("Agente encerrado.");
                GC.KeepAlive(mutex);
            }
        }
    }
}
