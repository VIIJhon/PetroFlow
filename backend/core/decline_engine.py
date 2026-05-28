"""
PetroFlow Decline Curve Analysis (DCA) Engine
Implements Arps decline curve equations (Exponential, Hyperbolic, and Harmonic)
to forecast oil well production and estimate Estimated Ultimate Recovery (EUR).
"""

import math
from typing import Dict, List, Any

class DeclineEngine:
    @staticmethod
    def calculate_exponential(qi: float, di_monthly: float, months: int) -> Dict[str, Any]:
        """
        Calculates Exponential decline: q(t) = qi * exp(-di * t)
        qi: Initial flow rate in bpd (barrels per day)
        di_monthly: Monthly nominal decline rate (fraction)
        months: Number of months to project
        """
        rates = []
        cumulative = []
        cum_prod = 0.0
        
        # Days per month conversion factor
        days_per_month = 30.4375
        
        for t in range(months + 1):
            # Production rate at month t
            qt = qi * math.exp(-di_monthly * t)
            rates.append(round(qt, 2))
            
            # Cumulative production in barrels (Np)
            if di_monthly > 0:
                # Analytic cumulative production: Np = (qi - qt) / di (in daily units converted to monthly)
                # qi and qt are daily, so daily cumulative is (qi - qt) / (di_monthly / days_per_month)
                di_daily = di_monthly / days_per_month
                np_val = (qi - qt) / di_daily
            else:
                np_val = qi * t * days_per_month
                
            cumulative.append(round(np_val, 2))
            
        eur = cumulative[-1] if cumulative else 0.0
        
        return {
            "rates_bpd": rates,
            "cumulative_bbl": cumulative,
            "eur_bbl": eur
        }

    @staticmethod
    def calculate_hyperbolic(qi: float, di_monthly: float, b: float, months: int) -> Dict[str, Any]:
        """
        Calculates Hyperbolic decline: q(t) = qi / (1 + b * di * t) ** (1/b)
        qi: Initial flow rate in bpd
        di_monthly: Monthly nominal decline rate (fraction)
        b: Decline exponent (0 < b < 1)
        months: Number of months to project
        """
        rates = []
        cumulative = []
        days_per_month = 30.4375
        
        # Bounds check for b
        b = max(0.01, min(0.99, b))
        
        for t in range(months + 1):
            # Production rate at month t
            factor = 1.0 + b * di_monthly * t
            qt = qi / (factor ** (1.0 / b))
            rates.append(round(qt, 2))
            
            # Cumulative production (Np)
            if di_monthly > 0:
                di_daily = di_monthly / days_per_month
                # Np = qi^b / (di*(1-b)) * (qi^(1-b) - qt^(1-b))
                np_val = (qi ** b) / (di_daily * (1.0 - b)) * (qi ** (1.0 - b) - qt ** (1.0 - b))
            else:
                np_val = qi * t * days_per_month
                
            cumulative.append(round(np_val, 2))
            
        eur = cumulative[-1] if cumulative else 0.0
        
        return {
            "rates_bpd": rates,
            "cumulative_bbl": cumulative,
            "eur_bbl": eur
        }

    @staticmethod
    def calculate_harmonic(qi: float, di_monthly: float, months: int) -> Dict[str, Any]:
        """
        Calculates Harmonic decline: q(t) = qi / (1 + di * t)
        qi: Initial flow rate in bpd
        di_monthly: Monthly nominal decline rate (fraction)
        months: Number of months to project
        """
        rates = []
        cumulative = []
        days_per_month = 30.4375
        
        for t in range(months + 1):
            # Production rate at month t
            qt = qi / (1.0 + di_monthly * t)
            rates.append(round(qt, 2))
            
            # Cumulative production (Np)
            if di_monthly > 0:
                di_daily = di_monthly / days_per_month
                # Np = (qi / di) * ln(qi / qt)
                np_val = (qi / di_daily) * math.log(qi / max(0.01, qt))
            else:
                np_val = qi * t * days_per_month
                
            cumulative.append(round(np_val, 2))
            
        eur = cumulative[-1] if cumulative else 0.0
        
        return {
            "rates_bpd": rates,
            "cumulative_bbl": cumulative,
            "eur_bbl": eur
        }

    @classmethod
    def run_decline_projection(cls, qi: float, di_annual_pct: float, b: float, months: int) -> Dict[str, Any]:
        """
        Runs full Arps projection based on decline parameters.
        qi: Initial flow rate in bpd
        di_annual_pct: Annual nominal decline rate in percent (e.g. 20.0 for 20%)
        b: Decline exponent (0 = Exponential, 1 = Harmonic, between = Hyperbolic)
        months: Duration of projection in months
        """
        # Convert annual decline percentage to monthly nominal decline
        di_annual = di_annual_pct / 100.0
        
        # di_monthly conversion: 1 - d_annual = (1 - d_monthly)^12 -> d_monthly = 1 - (1 - d_annual)^(1/12)
        if di_annual >= 1.0:
            di_monthly = 0.5  # Cap extreme nominal values
        elif di_annual > 0:
            di_monthly = 1.0 - ((1.0 - di_annual) ** (1.0 / 12.0))
        else:
            di_monthly = 0.0
            
        # Select appropriate model based on b
        if b <= 0.0:
            res = cls.calculate_exponential(qi, di_monthly, months)
            model_type = "Exponencial"
        elif b >= 1.0:
            res = cls.calculate_harmonic(qi, di_monthly, months)
            model_type = "Armonica"
        else:
            res = cls.calculate_hyperbolic(qi, di_monthly, b, months)
            model_type = "Hiperbolica"
            
        # Add labels for months
        time_series = [i for i in range(months + 1)]
        
        return {
            "model_type": model_type,
            "qi_bpd": qi,
            "di_annual_pct": di_annual_pct,
            "b_exponent": b,
            "months_projected": months,
            "time_months": time_series,
            "rates_bpd": res["rates_bpd"],
            "cumulative_bbl": res["cumulative_bbl"],
            "eur_bbl": res["eur_bbl"]
        }
