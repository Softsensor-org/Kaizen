# SPDX-License-Identifier: MIT
"""
Payer configuration for different insurance companies
"""

class PayerConfig:
    """Configuration for a specific payer"""
    def __init__(self, payer_id: str, payer_name: str, default_qualifier: str = "PI"):
        self.payer_id = payer_id
        self.payer_name = payer_name
        self.default_qualifier = default_qualifier

    def __repr__(self):
        return f"PayerConfig(id={self.payer_id}, name={self.payer_name})"


# Predefined payer configurations
PAYERS = {
    "UHC_CS": PayerConfig(
        payer_id="87726",
        payer_name="UNITED HEALTHCARE COMMUNITY & STATE",
        default_qualifier="PI"
    ),
    "UHC_KY": PayerConfig(
        payer_id="87726",
        payer_name="UNITED HEALTHCARE KENTUCKY",
        default_qualifier="PI"
    ),
    "AVAILITY": PayerConfig(
        payer_id="030240928",
        payer_name="AVAILITY",
        default_qualifier="46"
    ),
}


def get_payer_config(payer_key: str = None, payer_id: str = None, payer_name: str = None) -> PayerConfig:
    """
    Get payer configuration by key, ID, or name.

    Args:
        payer_key: Predefined payer key (e.g., "UHC_CS")
        payer_id: Payer ID (e.g., "87726")
        payer_name: Payer name (e.g., "UNITED HEALTHCARE")

    Returns:
        PayerConfig object

    Examples:
        >>> get_payer_config(payer_key="UHC_CS")
        >>> get_payer_config(payer_id="87726", payer_name="UNITED HEALTHCARE")
    """
    if payer_key and payer_key in PAYERS:
        return PAYERS[payer_key]

    if payer_id or payer_name:
        # Create custom payer config
        return PayerConfig(
            payer_id=payer_id or "",
            payer_name=payer_name or "",
            default_qualifier="PI"
        )

    # Default to UHC C&S
    return PAYERS["UHC_CS"]


def list_payers():
    """List all predefined payer configurations"""
    return {key: (cfg.payer_id, cfg.payer_name) for key, cfg in PAYERS.items()}
