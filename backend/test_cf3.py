import asyncio, json  
from services.deployment import DeploymentOrchestrator  
orch = DeploymentOrchestrator()  
result = asyncio.run(orch.deploy_to_cloudflare('../frontend', 'test-random-cf-proj-123456'))  
with open('cf_result3.json', 'w', encoding='utf-8') as f: json.dump(result, f, ensure_ascii=False)  
