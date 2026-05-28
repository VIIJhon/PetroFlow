import math

class LockhartMartinelliCorrelation:
    """Calculates void fraction using Lockhart-Martinelli correlation for two-phase flow."""
    @staticmethod
    def calculate_void_fraction(quality: float, density_gas: float, density_liquid: float, viscosity_gas: float, viscosity_liquid: float) -> float:
        """
        Calculate the void fraction based on the Chisholm correlation of the Lockhart-Martinelli parameter.
        """
        if quality <= 0.0:
            return 0.0
        if quality >= 1.0:
            return 1.0

        # Density and viscosity ratios
        rho_ratio = density_liquid / density_gas
        mu_ratio = viscosity_liquid / viscosity_gas

        # Lockhart-Martinelli parameter (X_tt for turbulent-turbulent)
        x_tt = ((1 - quality) / quality) ** 0.9 * (rho_ratio) ** -0.5 * (mu_ratio) ** 0.1
        
        # Void fraction using Chisholm correlation (C=20 for turbulent-turbulent)
        c = 20.0
        phi_l_squared = 1 + c / x_tt + 1 / (x_tt ** 2)
        
        # Simplified void fraction alpha
        # Alternatively, using the simplistic homogeneous or Zivi models if X_tt is complex.
        # We will use the common Zivi correlation for void fraction as an industry standard estimation
        # alpha = [1 + ((1-x)/x) * (rho_g/rho_l)^(2/3)]^-1
        
        void_fraction = 1.0 / (1.0 + ((1.0 - quality) / quality) * (density_gas / density_liquid) ** (2.0 / 3.0))
        return void_fraction

class MixedDensityCalculator:
    """Computes variable mixed density based on gas fraction."""
    @staticmethod
    def calculate_mixed_density(void_fraction: float, density_gas: float, density_liquid: float) -> float:
        """
        Calculate the homogeneous mixed density of a two-phase flow.
        """
        void_fraction = max(0.0, min(1.0, void_fraction))
        return void_fraction * density_gas + (1.0 - void_fraction) * density_liquid

class DNVErosionCorrosionModel:
    """Implements DNV RP O501 standard for erosion and corrosion rates."""
    @staticmethod
    def calculate_erosion_rate(fluid_velocity: float, particle_density: float, particle_diameter: float, sand_production_rate: float, pipe_diameter: float) -> float:
        """
        Simplified DNV RP O501 erosion rate prediction (mm/year).
        Assumes carbon steel pipe material.
        """
        # Material constant for Carbon Steel
        K = 2.0e-9
        
        # Velocity exponent (typically 2.6 for steel)
        n = 2.6
        
        # Cross sectional area
        area = math.pi * (pipe_diameter / 2.0) ** 2
        
        # Sand concentration (kg/m3)
        if area > 0 and fluid_velocity > 0:
            concentration = sand_production_rate / (fluid_velocity * area)
        else:
            concentration = 0.0

        # Erosion rate formula approximation
        erosion_rate = K * concentration * (fluid_velocity ** n)
        
        # Convert to mm/year (assuming continuous operation)
        # 1 m/s -> mm/yr conversion is roughly * 1000 * 3600 * 24 * 365
        erosion_rate_mm_yr = erosion_rate * 1000 * 31536000
        return erosion_rate_mm_yr

class SlurryWearPredictor:
    """Predicts wear rates in slurry transport systems."""
    @staticmethod
    def calculate_wear_rate(velocity: float, concentration_vol: float, particle_hardness: float, pipe_hardness: float) -> float:
        """
        Calculates slurry abrasive wear rate based on relative hardness and velocity.
        Result is an arbitrary severity index (0.0 to 10.0+).
        """
        if pipe_hardness <= 0:
            return 0.0
        
        hardness_ratio = particle_hardness / pipe_hardness
        
        # Velocity exponent for slurry is often around 3
        wear_index = (velocity ** 3) * concentration_vol * (hardness_ratio ** 1.2)
        
        return wear_index * 1e-4
