import asyncio, json  
from core.config import settings  
settings.CLOUDFLARE_API_TOKEN = ''  
from services.deployment import DeploymentOrchestrator  
orch = DeploymentOrchestrator()  
result = asyncio.run(orch.deploy_to_cloudflare('../frontend', 'test-proj-123'))  
print(result)  
