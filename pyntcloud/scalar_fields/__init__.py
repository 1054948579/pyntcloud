
"""
HAKUNA MATATA
"""

from .scalar_fields import *

SF_NORMALS = {
'inclination_deg': inclination_deg,
'inclination_rad': inclination_rad,
'orientation_deg': orientation_deg,
'orientation_rad': orientation_rad,
}

SF_RGB = {
'rgb_intensity' : (['Ri', 'Gi', 'Bi'], rgb_intensity),
'relative_luminance': relative_luminance,
'hsv' : (['H', 'S', 'V'], hsv)
}

SF_NEIGHBOURHOOD = {
'eigen_values': (['e1', 'e2', 'e3'], eigen_values),
'eigen_sum': eigen_sum,
'omnivariance': omnivariance,
'eigenentropy': eigenentropy,
'anisotropy': anisotropy,
'planarity': planarity,
'linearity': linearity,
'curvature': curvature,
'sphericity': sphericity,
'verticality':verticality
}

ALL_SF = "  ".join(SF_NORMALS.keys()) + " "\
        "  ".join(SF_RGB.keys()) + " "\
        "  ".join(SF_NEIGHBOURHOOD.keys())


