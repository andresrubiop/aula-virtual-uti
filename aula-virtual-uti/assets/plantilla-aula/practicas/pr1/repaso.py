"""PR1 · Retención estimada con y sin repasos (modelo ilustrativo R = exp(-t/S)).

Uso:  python3 practicas/pr1/repaso.py
"""
import math

S0 = 2.0          # estabilidad inicial, en días
FACTOR = 2.5      # cuánto crece la estabilidad con cada repaso
EXAMEN = 30       # día del examen


def retencion(repasos: list[int], dia: int) -> float:
    """Fracción recordada en `dia` si se repasa en los días de `repasos`."""
    s, ultimo = S0, 0
    for r in sorted(repasos):
        if r > dia:
            break
        s, ultimo = s * FACTOR, r
    return math.exp(-(dia - ultimo) / s)


if __name__ == '__main__':
    planes = {'sin repasos': [], 'un repaso (día 1)': [1], 'espaciado (1, 3, 7, 14)': [1, 3, 7, 14], 'todo la víspera (29)': [29]}
    for nombre, plan in planes.items():
        print(f'{nombre:26s} retención el día {EXAMEN}: {retencion(plan, EXAMEN) * 100:5.1f} %')
