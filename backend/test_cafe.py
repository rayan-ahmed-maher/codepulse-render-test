import asyncio  
from services.deployment import DeploymentOrchestrator  
orch = DeploymentOrchestrator()  
result = asyncio.run(orch.deploy_to_cloudflare('uploads/cafe-noir-indiranagar', 'cafe-noir-cf-test'))  
print(result)  
