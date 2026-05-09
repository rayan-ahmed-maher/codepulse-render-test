import asyncio, json  
from core.config import settings  
settings.CLOUDFLARE_ACCOUNT_ID = 'bad_account_id'  
from services.deployment import DeploymentOrchestrator  
orch = DeploymentOrchestrator()  
result = asyncio.run(orch.deploy_to_cloudflare('../frontend', 'test-proj'))  
print(result)  
