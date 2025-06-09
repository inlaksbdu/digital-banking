from difflib import SequenceMatcher
import re
from .models import CustomUser
import requests
from datetime import datetime
from user_agents import parse
import geoip2.database
import geoip2.errors
from typing import Dict


def isPasswordSimilar(password, email):
    max_similarity = 0.7
    password = password.lower()
    value_lower = email.lower()
    value_parts = re.split(r"\W+", value_lower) + [value_lower]
    for value_part in value_parts:
        if SequenceMatcher(a=password, b=value_part).quick_ratio() >= max_similarity:
            return True
    return False


def email_address_exists(email):
    return CustomUser.objects.filter(email__iexact=email).exists()


def get_login_notification_data(
    request,
    user_id: str,
    security_center_base_url: str = "https://cbkkenya.com/security",
) -> Dict[str, str]:
    """
    Extract login notification data from the request object.

    Args:
        request: Django/Flask request object or similar
        user_id: User identifier for personalized security URL
        security_center_base_url: Base URL for security center

    Returns:
        Dict containing all login notification template variables
    """

    def get_client_ip(request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded IP first (common in production with load balancers)
        x_forwarded_for = getattr(request, "META", {}).get(
            "HTTP_X_FORWARDED_FOR"
        ) or getattr(request.headers, "get", lambda x: None)("X-Forwarded-For")

        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            # Fallback to direct connection IP
            ip = (
                getattr(request, "META", {}).get("REMOTE_ADDR")
                or getattr(request, "remote_addr", None)
                or getattr(request, "environ", {}).get("REMOTE_ADDR", "Unknown")
            )

        return ip

    def get_user_agent_info(request) -> tuple:
        """Extract device and browser info from User-Agent header."""
        try:
            # Get user agent string
            user_agent_string = (
                getattr(request, "META", {}).get("HTTP_USER_AGENT")
                or getattr(request.headers, "get", lambda x: None)("User-Agent")
                or "Unknown"
            )

            # Parse user agent
            user_agent = parse(user_agent_string)

            # Extract device info
            device_info = f"{user_agent.device.family}"
            if user_agent.device.brand:
                device_info = f"{user_agent.device.brand} {device_info}"
            if user_agent.device.model:
                device_info = f"{device_info} {user_agent.device.model}"

            # Clean up device info
            if device_info.strip() == "Other":
                if user_agent.os.family != "Other":
                    device_info = f"{user_agent.os.family} Device"
                else:
                    device_info = "Desktop/Laptop"

            # Extract browser info
            browser_info = f"{user_agent.browser.family}"
            if user_agent.browser.version_string:
                browser_info = f"{browser_info} {user_agent.browser.version_string}"

            # Add OS info to browser
            if user_agent.os.family != "Other":
                browser_info = f"{browser_info} on {user_agent.os.family}"
                if user_agent.os.version_string:
                    browser_info = f"{browser_info} {user_agent.os.version_string}"

            return (
                device_info.strip() or "Unknown Device",
                browser_info.strip() or "Unknown Browser",
            )

        except Exception as e:
            print(f"Error parsing user agent: {e}")
            return "Unknown Device", "Unknown Browser"

    def get_location_from_ip(ip_address: str) -> str:
        """Get location information from IP address using GeoIP2."""
        try:
            # You need to download GeoLite2-City.mmdb from MaxMind
            # https://dev.maxmind.com/geoip/geoip2/geolite2/
            with geoip2.database.Reader("path/to/GeoLite2-City.mmdb") as reader:
                response = reader.city(ip_address)

                city = response.city.name or "Unknown City"
                country = response.country.name or "Unknown Country"

                if city != "Unknown City" and country != "Unknown Country":
                    return f"{city}, {country}"
                elif country != "Unknown Country":
                    return country
                else:
                    return "Unknown Location"

        except (geoip2.errors.AddressNotFoundError, FileNotFoundError, Exception) as e:
            print(f"GeoIP lookup failed: {e}")

            # Fallback: Try to get basic location info from a free API
            try:
                response = requests.get(
                    f"http://ip-api.com/json/{ip_address}", timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "success":
                        city = data.get("city", "")
                        country = data.get("country", "")
                        if city and country:
                            return f"{city}, {country}"
                        elif country:
                            return country
            except Exception as api_error:
                print(f"IP API lookup failed: {api_error}")

            return "Unknown Location"

    def format_login_time() -> str:
        """Format current time for login notification."""
        now = datetime.now()
        return now.strftime("%B %d, %Y at %I:%M %p %Z").replace("  ", " ")

    def generate_security_center_url(base_url: str, user_id: str) -> str:
        """Generate personalized security center URL."""
        return f"{base_url.rstrip('/')}/dashboard?user_id={user_id}"

    # Extract all the required information
    try:
        ip_address = get_client_ip(request)
        device, browser = get_user_agent_info(request)
        location = get_location_from_ip(ip_address)
        login_time = format_login_time()
        security_url = generate_security_center_url(security_center_base_url, user_id)

        return {
            "loginTime": login_time,
            "device": device,
            "ipAddress": ip_address,
            "location": location,
            "browser": browser,
            "securityCenterUrl": security_url,
        }

    except Exception as e:
        print(f"Error generating login notification data: {e}")
        # Return safe defaults
        return {
            "loginTime": format_login_time(),
            "device": "Unknown Device",
            "ipAddress": "Unknown",
            "location": "Unknown Location",
            "browser": "Unknown Browser",
            "securityCenterUrl": generate_security_center_url(
                security_center_base_url, user_id
            ),
        }
