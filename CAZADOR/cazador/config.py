"""§1 CONFIGURACIÓN: único sitio que hay que editar.

Los porcentajes se escriben como en el prompt (0.05 = 0,05 %) y las propiedades
``*_frac`` los convierten a fracciones (0.0005) que es lo que usa el motor.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict


@dataclass
class Config:
    margen_por_operacion_usd: float = 20.0
    apalancamiento: float = 10.0                 # posición = 200 $
    comision_taker_pct: float = 0.05             # por lado
    comision_maker_pct: float = 0.02
    deslizamiento_min_pct: float = 0.02          # por lado; el motor lo aumenta en monedas poco líquidas
    periodo_busqueda_meses: int = 24             # mínimo 12
    holdout_meses: int = 2                       # bloqueados hasta el final
    periodo_segundos: str = "4 semanas por régimen + últimas 4 semanas"
    objetivos_beneficio_pct_margen: tuple = (5, 10, 20, 30, 50)
    max_posiciones_simultaneas: int = 5
    estrategias_aptas_objetivo: int = 3
    region_api_bloqueada: bool = True            # fapi.binance.com devuelve 451 desde este entorno -> solo data.binance.vision

    # Parámetros del motor que NO están en §1 pero hay que fijar (documentados):
    mantenimiento_margen_frac: float = 0.005     # margen de mantenimiento (liquidación), aprox. tramo 1 de Binance
    objetivo_es_maker: bool = False              # conservador: el objetivo también paga comisión taker
    semilla: int = 20250930

    # --- derivadas -------------------------------------------------------
    @property
    def nocional_usd(self) -> float:
        return self.margen_por_operacion_usd * self.apalancamiento

    @property
    def fee_taker(self) -> float:
        return self.comision_taker_pct / 100.0

    @property
    def fee_maker(self) -> float:
        return self.comision_maker_pct / 100.0

    @property
    def slip_min(self) -> float:
        return self.deslizamiento_min_pct / 100.0

    def objetivo_frac_precio(self, pct_margen: float) -> float:
        """'Salgo en cuanto gano X % del margen' -> movimiento de precio necesario (fracción)."""
        return pct_margen / 100.0 / self.apalancamiento

    def como_dict(self) -> dict:
        return asdict(self)


CFG = Config()
