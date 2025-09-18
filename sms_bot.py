from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import requests

app = Flask(__name__)

# Configuración de seguridad
ALLOWED_NUMBERS = ["+5491154676529"]  # tu número con código país
PIN = "6606"  # código secreto que vos elegís

# Estado por número de teléfono
users = {}  # {telefono: {'state': estado, 'temp': {}}}

ACCESS_TOKEN = "TU_ACCESS_TOKEN"  # tu token Mercado Pago

def get_saldo():
    url = "https://api.mercadopago.com/v1/account/balance"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        total = sum([item['balance'] for item in data])
        return total
    return None

def transferir(monto, destino_id):
    url = "https://api.mercadopago.com/v1/payments"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    data = {
        "transaction_amount": monto,
        "description": "Transferencia via bot SMS",
        "payment_method_id": "account_money",
        "payer": {"type": "registered", "id": destino_id}
    }
    r = requests.post(url, headers=headers, json=data)
    if r.status_code == 201:
        return True, None
    else:
        return False, r.text

@app.route("/sms", methods=['POST'])
def sms_reply():
    from_number = request.form['From']
    body = request.form['Body'].strip()
    resp = MessagingResponse()

    # Verificamos número
    if from_number not in ALLOWED_NUMBERS:
        resp.message("Número no autorizado ❌")
        return str(resp)

    user = users.get(from_number, {'state': 'pin', 'temp': {}})
    state = user['state']
    temp = user['temp']

    if state == 'pin':
        if body == PIN:
            resp.message("PIN correcto ✅\nMenú:\n1. Ver saldo\n2. Transferir\n3. Comprar")
            user['state'] = 'menu'
        else:
            resp.message("PIN incorrecto ❌. Reingresalo.")
    elif state == 'menu':
        if body == '1':
            saldo = get_saldo()
            if saldo is not None:
                resp.message(f"Tu saldo es: ${saldo}")
            else:
                resp.message("Error al consultar saldo")
            user['state'] = 'pin'  # pedimos PIN otra vez para la próxima operación
        elif body == '2':
            resp.message("Ingrese monto y destinatario separados por coma (ej: 100,1234567890)")
            user['state'] = 'transferir'
        else:
            resp.message("Opción inválida. Volviendo al menú principal.")
            user['state'] = 'pin'
    elif state == 'transferir':
        try:
            monto_str, destino = body.split(',')
            monto = float(monto_str.strip())
            destino = destino.strip()
            temp['monto'] = monto
            temp['destino'] = destino
            resp.message(f"Confirma transferencia de ${monto} a {destino}:\n1. Sí\n2. No")
            user['state'] = 'confirm_transfer'
        except:
            resp.message("Formato inválido. Intenta: monto,destino (ej: 100,1234567890)")
    elif state == 'confirm_transfer':
        if body == '1':
            exito, error = transferir(temp['monto'], temp['destino'])
            if exito:
                resp.message("Transferencia realizada con éxito ✅")
            else:
                resp.message(f"Error al transferir: {error}")
            user['state'] = 'pin'
            user['temp'] = {}
        else:
            resp.message("Transferencia cancelada ❌")
            user['state'] = 'pin'
            user['temp'] = {}

    users[from_number] = user
    return str(resp)

if __name__ == "__main__":
    app.run(debug=True)
