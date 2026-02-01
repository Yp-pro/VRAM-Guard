import psutil
import hashlib
import uuid
import logging

logger = logging.getLogger(__name__)

class LicenseManager:
    """
    Manages the application's licensing status and hardware binding.
    
    NOTE: This is a placeholder for a robust licensing system (v2.0). 
    For v1.4, it simply returns False to lock Pro features.
    """
    
    def __init__(self, license_file: str = "license.dat"):
        """
        Initializes the LicenseManager.
        :param license_file: The file where the license hash is stored.
        """
        self.license_file = license_file
        self._is_pro_active = False
        
        # In a real scenario, this would trigger a check
        # self._check_license()

    def _get_hardware_id(self) -> str:
        """
        Generates a unique hardware ID (HWID) for binding the license.
        Uses the primary MAC address and the system UUID.
        """
        try:
            # Get MAC address of the first non-loopback, non-virtual interface
            mac_address = ""
            for interface, addrs in psutil.net_if_addrs().items():
                if interface.startswith("Loopback") or interface.startswith("vEthernet"):
                    continue
                for addr in addrs:
                    if addr.family == psutil.AF_LINK and addr.address:
                        mac_address = addr.address
                        break
                if mac_address: break

            # Get system UUID (more stable)
            system_uuid = str(uuid.getnode())

            hwid = f"{mac_address}-{system_uuid}"
            logger.debug(f"Generated HWID: {hwid}")
            return hwid
        except Exception as e:
            logger.error(f"Failed to generate HWID: {e}")
            return "DEFAULT_HWID"

    def is_pro_active(self) -> bool:
        """
        Checks if the Pro features are active.
        In v1.4, this is a placeholder returning False.
        """
        return self._is_pro_active

    def activate_pro(self, key: str) -> bool:
        """
        Simulates the activation process (for future implementation).
        In a real scenario, this would contact a server or hash the key.
        """
        if key == "PRO_KEY_FOR_TESTING":
            self._is_pro_active = True
            logger.warning("PRO features activated with hardcoded test key.")
            return True
        
        # Future implementation:
        # hwid = self._get_hardware_id()
        # generated_hash = hashlib.sha256(f"{key}{hwid}".encode()).hexdigest()
        # self._save_hash(generated_hash)
        
        return False