from database import get_connection, init_db

def seed_cuentas_casa_padres():
    conn = get_connection()
    cursor = conn.cursor()

    cuentas = [
        ('casa_padres', 'Luz',            '1639389-4',  85867, 'compartido', 'https://www.enel.cl/es/clientes/servicios-en-linea/pago-de-cuenta.html', 24),
        ('casa_padres', 'Gas',            '800193249',  50517, 'compartido', 'https://www.metrogas.cl/pagar-mi-cuenta', 21),
        ('casa_padres', 'Agua',           '1567571-3',  32780, 'compartido', 'https://www.aguasandinas.cl/web/aguasandinas/pagar-mi-cuenta', None),
        ('casa_padres', 'Autopistas TAG', '9831630-2',  17560, 'mama',       'https://tagtotal.cl/', 17),
        ('casa_padres', 'Celular WOM',    '10211025-0', 17990, 'mama',       'https://www.wom.cl/paga-aqui/', 15),
        ('casa_padres', 'Internet VTR',   '17429113-6', 15990, 'compartido', 'https://vtr.com/portaldepagos/initial', 25),
        ('casa_padres', 'Gastos Comunes', 'casa_65',    0,     'compartido', '', None),
    ]

    cursor.executemany('''
        INSERT INTO cuentas_fijas (propiedad, nombre, identificador, monto_estimado, responsable, url_pago, dia_vencimiento)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', cuentas)

    conn.commit()
    conn.close()
    print("Cuentas precargadas correctamente")

if __name__ == '__main__':
    init_db()
    seed_cuentas_casa_padres()