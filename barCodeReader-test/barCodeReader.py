import barcode
from barcode.writer import ImageWriter
from pyzbar.pyzbar import decode
from PIL import Image
import io
import time

def identify_barcode_type_and_data(image):
    """Identifica o tipo e os dados do código de barras em uma imagem."""
    decoded_objects = decode(image)
    if decoded_objects:
        # Para simplificar, apenas usa o primeiro objeto detectado
        barcode_type = decoded_objects[0].type
        barcode_data = decoded_objects[0].data.decode('utf-8')
        return barcode_type, barcode_data
    return None, None

def map_barcode_type(type_str):
    """Mapeia o tipo de código de barras detectado para um tipo suportado pelo barcode."""
    if type_str == 'EAN13':
        return 'ean13'
    elif type_str == 'ITF':
        return 'itf'
    elif type_str == 'CODE39':
        return 'code39'
    elif type_str == 'CODE128':
        return 'code128'
    else:
        raise ValueError('Tipo de código de barras não suportado.')

def generate_barcode_image(code_type, data, output_path):
    """Gera uma imagem de código de barras com o tipo e dados fornecidos."""
    try:
        barcode_class = barcode.get_barcode_class(code_type)
        barcode_instance = barcode_class(data, writer=ImageWriter())
        barcode_instance.save(output_path)
        print(f'Imagem gerada: {output_path}')
    except Exception as e:
        print(f'Erro ao gerar imagem: {e}')

def main():
   
    print("BILLFLUX TEST ")
    
    while True:
        # Solicita ao usuário para inserir os dados do código de barras
        barcode_data = input("Digite os dados do código de barras: ").strip()
        
        if barcode_data.lower() == 'sair':
            print("Encerrando o programa.")
            break

        if not barcode_data:
            print('Nenhum dado de código de barras fornecido.')
            continue

        # Tipo fixo para testes (pode ser ajustado conforme necessário)
        barcode_type = 'EAN13'  # Ajuste conforme necessário

        print(f'Tipo de código de barras: {barcode_type}')
        print(f'Dados do código de barras: {barcode_data}')

        try:
            code_type = map_barcode_type(barcode_type)
            if code_type and barcode_data:
                # Gera uma nova imagem com o mesmo tipo e dados
                generate_barcode_image(code_type, barcode_data, output_path)
                output_path = f'output_barcode_{int(time.time())}.png'
            else:
                print('Nenhum código de barras detectado.')
        except ValueError as e:
            print(f'Erro: {e}')

if __name__ == '__main__':
    main()
