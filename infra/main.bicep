targetScope = 'subscription'

@minLength(1)
@maxLength(32)
param environmentName string
param location string = 'eastus'
@minLength(1)
param publisherEmail string
param publisherName string = 'APIM weather walkthrough'
@minLength(1)
param weatherContact string
@minLength(1)
param developerEmail string
@minLength(1)
param modelEndpoint string
@minLength(1)
param modelDeployment string

var suffix = uniqueString(subscription().id, environmentName, location)
var tags = {
  SecurityControl: 'Ignore'
  'azd-env-name': environmentName
  purpose: 'disposable-apim-walkthrough'
}

resource group 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: 'rg-apim-${environmentName}'
  location: location
  tags: tags
}

module demo 'demo.bicep' = {
  name: 'apim-demo'
  scope: group
  params: {
    location: location
    suffix: suffix
    tags: tags
    publisherEmail: publisherEmail
    publisherName: publisherName
    weatherContact: weatherContact
  }
}

output AZURE_RESOURCE_GROUP string = group.name
output APIM_NAME string = demo.outputs.apimName
output APIM_RESOURCE_ID string = demo.outputs.apimId
output APIM_GATEWAY_URL string = demo.outputs.gatewayUrl
output DEVELOPER_PORTAL_URL string = demo.outputs.portalUrl
output MCP_URL string = '${demo.outputs.gatewayUrl}/weather-mcp/mcp'
output LOG_ANALYTICS_WORKSPACE_ID string = demo.outputs.workspaceId
output APPLICATION_INSIGHTS_NAME string = demo.outputs.insightsName
output DEMO_DEVELOPER_EMAIL string = developerEmail
output AZURE_OPENAI_ENDPOINT string = modelEndpoint
output AZURE_OPENAI_DEPLOYMENT string = modelDeployment
