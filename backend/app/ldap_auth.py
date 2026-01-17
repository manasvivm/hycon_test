# backend/app/ldap_auth.py
"""
Active Directory LDAP Authentication Module
Domain: hyconlab.com
"""

from ldap3 import Server, Connection, ALL, NTLM, ALL_ATTRIBUTES
from typing import Optional, Dict
import os
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

class LDAPConfig:
    """LDAP Configuration for HyCON Active Directory"""
    
    LDAP_SERVER = os.getenv("LDAP_SERVER", "WIN-PALNGRANPOS.hyconlab.com")
    LDAP_PORT = int(os.getenv("LDAP_PORT", "389"))
    LDAP_USE_SSL = os.getenv("LDAP_USE_SSL", "false").lower() == "true"
    
    LDAP_DOMAIN = os.getenv("LDAP_DOMAIN", "hyconlab.com")
    LDAP_NETBIOS = os.getenv("LDAP_NETBIOS", "HYCONLAB")
    
    LDAP_BASE_DN = os.getenv("LDAP_BASE_DN", "DC=hyconlab,DC=com")
    LDAP_USER_SEARCH_BASE = os.getenv("LDAP_USER_SEARCH_BASE", "CN=Users,DC=hyconlab,DC=com")
    
    # Enable/disable LDAP authentication
    LDAP_ENABLED = os.getenv("LDAP_ENABLED", "true").lower() == "true"

class LDAPAuthenticator:
    """Active Directory LDAP Authentication"""
    
    def __init__(self):
        self.config = LDAPConfig()
        self.server = Server(
            self.config.LDAP_SERVER,
            port=self.config.LDAP_PORT,
            use_ssl=self.config.LDAP_USE_SSL,
            get_info=ALL
        )
        logger.info(f"LDAP initialized for domain: {self.config.LDAP_DOMAIN}")
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """
        Authenticate user against Active Directory
        
        Args:
            username: Username (accepts: jsmith, HYCONLAB\\jsmith, jsmith@hyconlab.com)
            password: User's password
            
        Returns:
            Dict with user info if successful, None if failed
        """
        if not self.config.LDAP_ENABLED:
            logger.info("LDAP authentication is disabled")
            return None
            
        try:
            # Clean username and try different formats
            clean_username = self._clean_username(username)
            
            user_formats = [
                f"{self.config.LDAP_NETBIOS}\\{clean_username}",  # HYCONLAB\username
                f"{clean_username}@{self.config.LDAP_DOMAIN}",    # username@hyconlab.com
            ]
            
            connection = None
            authenticated_format = None
            
            for user_format in user_formats:
                try:
                    logger.info(f"Attempting LDAP auth: {user_format}")
                    
                    connection = Connection(
                        self.server,
                        user=user_format,
                        password=password,
                        authentication=NTLM,
                        auto_bind=True
                    )
                    
                    authenticated_format = user_format
                    logger.info(f"✅ LDAP authentication successful: {user_format}")
                    break
                    
                except Exception as auth_error:
                    logger.warning(f"❌ Auth failed for {user_format}: {str(auth_error)}")
                    continue
            
            if not connection or not authenticated_format:
                logger.error(f"All authentication attempts failed for: {username}")
                return None
            
            # Get user information from AD
            user_info = self._get_user_info(connection, clean_username)
            connection.unbind()
            
            return user_info
            
        except Exception as e:
            logger.error(f"LDAP authentication error for {username}: {str(e)}")
            return None
    
    def _clean_username(self, username: str) -> str:
        """Extract clean username from various formats"""
        # Remove domain prefix: HYCONLAB\username -> username
        if '\\' in username:
            username = username.split('\\')[-1]
        # Remove domain suffix: username@hyconlab.com -> username
        if '@' in username:
            username = username.split('@')[0]
        return username.strip()
    
    def _get_user_info(self, connection: Connection, username: str) -> Dict:
        """Get user information from Active Directory"""
        try:
            search_filter = f"(&(objectClass=user)(sAMAccountName={username}))"
            
            success = connection.search(
                search_base=self.config.LDAP_USER_SEARCH_BASE,
                search_filter=search_filter,
                attributes=ALL_ATTRIBUTES
            )
            
            if success and len(connection.entries) > 0:
                entry = connection.entries[0]
                
                # Extract user attributes safely
                email = str(entry.mail) if hasattr(entry, 'mail') else f"{username}@{self.config.LDAP_DOMAIN}"
                display_name = str(entry.displayName) if hasattr(entry, 'displayName') else username
                first_name = str(entry.givenName) if hasattr(entry, 'givenName') else ""
                last_name = str(entry.sn) if hasattr(entry, 'sn') else ""
                department = str(entry.department) if hasattr(entry, 'department') else ""
                title = str(entry.title) if hasattr(entry, 'title') else ""
                groups = [str(g) for g in entry.memberOf] if hasattr(entry, 'memberOf') else []
                
                user_info = {
                    'username': username,
                    'email': email,
                    'name': display_name or f"{first_name} {last_name}".strip() or username,
                    'first_name': first_name,
                    'last_name': last_name,
                    'department': department,
                    'title': title,
                    'groups': groups,
                    'role': self._determine_role(groups),
                    'source': 'ldap'
                }
                
                logger.info(f"Retrieved AD info for {username}: role={user_info['role']}, groups={len(groups)}")
                return user_info
            else:
                # Return minimal info if search fails
                return self._minimal_user_info(username)
                
        except Exception as e:
            logger.error(f"Error getting user info for {username}: {str(e)}")
            return self._minimal_user_info(username)
    
    def _minimal_user_info(self, username: str) -> Dict:
        """Return minimal user info when AD lookup fails"""
        return {
            'username': username,
            'email': f"{username}@{self.config.LDAP_DOMAIN}",
            'name': username,
            'first_name': '',
            'last_name': '',
            'department': '',
            'title': '',
            'groups': [],
            'role': 'user',
            'source': 'ldap'
        }
    
    def _determine_role(self, groups: list) -> str:
        """
        Determine user role based on AD group membership
        
        Customize group names based on your organization
        """
        groups_lower = [group.lower() for group in groups]
        
        # Admin groups (customize these for your organization)
        admin_groups = [
            'domain admins',
            'administrators',
            'hycon_admins',
            'hycon admins',
            'lab_administrators',
            'lab administrators',
            'equipment_managers',
            'equipment managers'
        ]
        
        for admin_group in admin_groups:
            if any(admin_group in group for group in groups_lower):
                logger.info(f"User granted admin role via group: {admin_group}")
                return 'admin'
        
        # Manager groups
        manager_groups = [
            'lab_managers',
            'lab managers',
            'department_heads',
            'department heads',
            'supervisors'
        ]
        
        for manager_group in manager_groups:
            if any(manager_group in group for group in groups_lower):
                logger.info(f"User granted manager role via group: {manager_group}")
                return 'manager'
        
        # Default role
        return 'user'
    
    def test_connection(self) -> Dict:
        """Test LDAP connection"""
        try:
            test_conn = Connection(self.server, auto_bind=True)
            
            success = test_conn.search(
                search_base=self.config.LDAP_BASE_DN,
                search_filter="(objectClass=domain)",
                attributes=['name']
            )
            
            test_conn.unbind()
            
            return {
                'success': True,
                'message': f'LDAP connection successful to {self.config.LDAP_DOMAIN}',
                'server': self.config.LDAP_SERVER,
                'domain': self.config.LDAP_DOMAIN
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'server': self.config.LDAP_SERVER
            }

# Global LDAP authenticator instance
ldap_auth = LDAPAuthenticator()
