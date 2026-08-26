import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from db.database import get_connection, init_db

def seed_cuentas_departamento():
    conn = get_connection()

    # Verificar si ya existen para no duplicar
    existe = conn.execute(
        "SELECT COUNT(*) as n FROM cuentas_fijas WHERE propiedad = 'departamento'"
    ).fetchone()["n"]

    if existe > 0:
        print("Cuentas del departamento ya existen, saltando seed.")
        conn.close()
        return

    cuentas = [
        ('departamento', 'Luz',             '303877-7',      83207, 'nico', 'https://www.enel.cl/es/clientes/servicios-en-linea/pago-de-cuenta.html', 21),
        ('departamento', 'Gas',             '000434001536',  70263, 'nico', 'https://sucursalvirtual.metrogas.cl/publico/procedimiento_de_pago',       15),
        ('departamento', 'Internet VTR',    '17429113-6',    25990, 'nico', 'https://vtr.com/portaldepagos/initial',                                   25),
        ('departamento', 'Gastos Comunes',  'depa_411',     130000, 'nico', '',                                                                        None),
    ]

    conn.executemany('''
        INSERT INTO cuentas_fijas (propiedad, nombre, identificador, monto_estimado, responsable, url_pago, dia_vencimiento)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', cuentas)

    conn.commit()
    conn.close()
    print("Cuentas del departamento cargadas OK")

if __name__ == '__main__':
    init_db()
    seed_cuentas_departamento()
