#!/usr/bin/env python3
"""
Test script for Code Server integration in Suna AI
Tests the complete integration from backend to frontend
"""

import asyncio
import aiohttp
import json
import sys
import time
from typing import Dict, Any

class CodeServerIntegrationTest:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.code_server_url = "http://localhost:8080"
        
    async def test_backend_api(self) -> bool:
        """Test backend Code Server API endpoints"""
        print("🧪 Testing Backend API...")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Test health endpoint
                async with session.get(f"{self.base_url}/health") as resp:
                    if resp.status != 200:
                        print(f"❌ Backend health check failed: {resp.status}")
                        return False
                
                # Test Code Server status endpoint
                async with session.get(f"{self.base_url}/api/code-server/status") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"✅ Code Server status: {data}")
                    else:
                        print(f"⚠️  Code Server status endpoint returned: {resp.status}")
                
                # Test Code Server start endpoint
                test_sandbox_id = "test-sandbox-123"
                async with session.post(
                    f"{self.base_url}/api/code-server/start",
                    json={"sandbox_id": test_sandbox_id}
                ) as resp:
                    if resp.status in [200, 201]:
                        data = await resp.json()
                        print(f"✅ Code Server start response: {data}")
                    else:
                        print(f"⚠️  Code Server start returned: {resp.status}")
                
                return True
                
        except Exception as e:
            print(f"❌ Backend API test failed: {e}")
            return False
    
    async def test_code_server_direct(self) -> bool:
        """Test direct connection to Code Server"""
        print("🧪 Testing Code Server Direct Connection...")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Test Code Server health
                async with session.get(f"{self.code_server_url}/healthz") as resp:
                    if resp.status == 200:
                        print("✅ Code Server is running and healthy")
                        return True
                    else:
                        print(f"⚠️  Code Server health check returned: {resp.status}")
                        return False
                        
        except Exception as e:
            print(f"❌ Code Server direct test failed: {e}")
            return False
    
    def test_frontend_components(self) -> bool:
        """Test that frontend components exist"""
        print("🧪 Testing Frontend Components...")
        
        import os
        
        components_to_check = [
            "frontend/src/components/code-editor/CodeServerIframe.tsx",
            "frontend/src/components/code-editor/CodeEditorPanel.tsx",
            "frontend/src/components/code-editor/index.ts",
            "frontend/src/components/thread/code-server-modal.tsx",
        ]
        
        all_exist = True
        for component in components_to_check:
            full_path = os.path.join(os.path.dirname(__file__), component)
            if os.path.exists(full_path):
                print(f"✅ {component} exists")
            else:
                print(f"❌ {component} missing")
                all_exist = False
        
        return all_exist
    
    def test_backend_components(self) -> bool:
        """Test that backend components exist"""
        print("🧪 Testing Backend Components...")
        
        import os
        
        components_to_check = [
            "backend/services/code_server_manager.py",
            "backend/services/code_server_api.py",
            "backend/agent/tools/enhanced_web_dev_tool.py",
            "backend/services/code_server/startup.sh",
            "backend/services/code_server/settings.json",
            "backend/services/code_server/extensions.json",
        ]
        
        all_exist = True
        for component in components_to_check:
            full_path = os.path.join(os.path.dirname(__file__), component)
            if os.path.exists(full_path):
                print(f"✅ {component} exists")
            else:
                print(f"❌ {component} missing")
                all_exist = False
        
        return all_exist
    
    def test_docker_config(self) -> bool:
        """Test Docker configuration"""
        print("🧪 Testing Docker Configuration...")
        
        import os
        import yaml
        
        try:
            docker_compose_path = os.path.join(os.path.dirname(__file__), "docker-compose.yaml")
            
            if not os.path.exists(docker_compose_path):
                print("❌ docker-compose.yaml not found")
                return False
            
            with open(docker_compose_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Check if code-server service exists
            if 'code-server' not in config.get('services', {}):
                print("❌ code-server service not found in docker-compose.yaml")
                return False
            
            code_server_config = config['services']['code-server']
            
            # Check essential configurations
            checks = [
                ('image', 'codercom/code-server:latest'),
                ('ports', ['8080:8080']),
            ]
            
            for key, expected in checks:
                if key not in code_server_config:
                    print(f"❌ {key} not found in code-server config")
                    return False
                
                if key == 'ports' and '8080:8080' not in str(code_server_config[key]):
                    print(f"❌ Port 8080 not properly configured")
                    return False
            
            print("✅ Docker configuration looks good")
            return True
            
        except Exception as e:
            print(f"❌ Docker config test failed: {e}")
            return False
    
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all integration tests"""
        print("🚀 Starting Code Server Integration Tests...\n")
        
        results = {}
        
        # Test components first (these don't require running services)
        results['frontend_components'] = self.test_frontend_components()
        print()
        
        results['backend_components'] = self.test_backend_components()
        print()
        
        results['docker_config'] = self.test_docker_config()
        print()
        
        # Test running services
        results['code_server_direct'] = await self.test_code_server_direct()
        print()
        
        results['backend_api'] = await self.test_backend_api()
        print()
        
        return results
    
    def print_summary(self, results: Dict[str, bool]):
        """Print test summary"""
        print("=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        passed = sum(results.values())
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title()}: {status}")
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! Code Server integration is ready!")
        else:
            print("⚠️  Some tests failed. Please check the issues above.")
            
        return passed == total

async def main():
    """Main test function"""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = "http://localhost:8000"
    
    tester = CodeServerIntegrationTest(base_url)
    results = await tester.run_all_tests()
    success = tester.print_summary(results)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    # Install required packages if not available
    try:
        import aiohttp
        import yaml
    except ImportError:
        print("Installing required packages...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "aiohttp", "pyyaml"])
        import aiohttp
        import yaml
    
    asyncio.run(main())