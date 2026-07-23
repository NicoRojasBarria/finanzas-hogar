from database import get_connection, init_db

def seed_cuentas_casa_padres():
    conn = get_connection()
    cursor = conn.cursor()

    cuentas = [
        ('casa_padres', 'Luz',        '1639389-4',  0, 'compartido'),
        ('casa_padres', 'Gas',        '800193249',  0, 'compartido'),
        ('casa_padres', 'Agua',       '1567571-3',  0, 'compartido'),
        ('casa_padres', 'Autopistas', '9831630-2',  0, 'mama'),
        ('casa_padres', 'Celular WOM','10211025-0', 0, 'mama'),
        ('casa_padres', 'Gastos Comunes', 'casa_65', 0, 'compartido'),
    ]

    cursor.executemany('''
        INSERT INTO cuentas_fijas (propiedad, nombre, identificador, monto_estimado, responsable)
        VALUES (?, ?, ?, ?, ?)
    ''', cuentas)

    conn.commit()
    conn.close()
    print("Cuentas precargadas correctamente")

if __name__ == '__main__':
    init_db()
    seed_cuentas_casa_padres()