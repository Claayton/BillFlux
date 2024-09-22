import barcode
from barcode.writer import ImageWriter
from datetime import datetime, timedelta

# Função para converter o fator de vencimento em uma data legível
def calcular_data_vencimento(fator_vencimento):
    data_base = datetime(1997, 10, 7)
    dias = int(fator_vencimento)
    data_vencimento = data_base + timedelta(days=dias)
    return data_vencimento.strftime("%d-%m-%Y")

# Função para gerar o código de barras em formato SVG (Intercalado 2 de 5)
def gerar_codigo_barras_svg(codigo_barras, nome_arquivo):
    I2of5 = barcode.get_barcode_class('itf')  # Usamos a classe correta: Interleaved 2 of 5 (I2of5)
    codigo_barra_svg = I2of5(codigo_barras, writer=ImageWriter())

    # Salvando o código de barras no formato SVG
    codigo_barra_svg.save(nome_arquivo, options={"write_text": False})

# Função para ler o código de barras e separar as informações
def ler_codigo_barras(codigo_barras):
    if len(codigo_barras) != 44:
        raise ValueError("O código de barras deve ter 44 dígitos")

    banco = codigo_barras[0:3]
    moeda = codigo_barras[3]
    digito_verificador = codigo_barras[4]
    fator_vencimento = codigo_barras[5:9]
    valor = codigo_barras[9:19]
    campo_livre = codigo_barras[19:44]

    # Convertendo o valor para um formato monetário
    valor_reais = float(valor) / 100
    valor_formatado = f"R$ {valor_reais:,.2f}"

    # Convertendo o fator de vencimento para uma data legível
    data_vencimento = calcular_data_vencimento(fator_vencimento)

    return {
        "banco": banco,
        "moeda": moeda,
        "digito_verificador": digito_verificador,
        "data_vencimento": data_vencimento,
        "valor": valor_formatado,
        "campo_livre": campo_livre
    }

# Função principal que executa o loop e o menu
def main():
    while True:
        print("\n--- Menu ---")
        print("1. Gerar código de barras")
        print("2. Sair")
        opcao = input("Escolha uma opção: ")

        if opcao == '1':
            codigo_barras = input("Digite o código de barras (44 dígitos): ")
            try:
                resultado = ler_codigo_barras(codigo_barras)

                # Exibe os detalhes
                for chave, valor in resultado.items():
                    print(f"{chave}: {valor}")
                
                # Gera a imagem SVG do código de barras no padrão FEBRABAN
                nome_arquivo = f"boleto_{resultado['data_vencimento']}.svg"
                gerar_codigo_barras_svg(codigo_barras, nome_arquivo)
                print(f"Imagem do código de barras gerada com sucesso! Nome do arquivo: {nome_arquivo}")

            except ValueError as e:
                print(e)
        
        elif opcao == '2':
            print("Saindo...")
            break
        
        else:
            print("Opção inválida. Tente novamente.")

if __name__ == "__main__":
    main()
