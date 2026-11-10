param location string
param suffix string
param tags object
param publisherEmail string
param publisherName string
param weatherContact string

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'log-apim-${suffix}'
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource insights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'appi-apim-${suffix}'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: workspace.id
    DisableLocalAuth: true
  }
}

resource apim 'Microsoft.ApiManagement/service@2024-05-01' = {
  name: 'apim-weather-${suffix}'
  location: location
  tags: tags
  sku: { name: 'StandardV2', capacity: 1 }
  identity: { type: 'SystemAssigned' }
  properties: {
    publisherEmail: publisherEmail
    publisherName: publisherName
    developerPortalStatus: 'Enabled'
    publicNetworkAccess: 'Enabled'
    virtualNetworkType: 'None'
  }
}

resource telemetryRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(insights.id, apim.id, 'metrics-publisher')
  scope: insights
  properties: {
    principalId: apim.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '3913510d-42f4-4e42-8a64-420c390055eb')
  }
}

resource logger 'Microsoft.ApiManagement/service/loggers@2024-05-01' = {
  parent: apim
  name: 'application-insights'
  properties: {
    loggerType: 'applicationInsights'
    credentials: {
      connectionString: insights.properties.ConnectionString
      identityClientId: 'SystemAssigned'
    }
    resourceId: insights.id
    isBuffered: true
  }
  dependsOn: [telemetryRole]
}

var safePipelineLog = {
  request: { body: { bytes: 0 }, headers: ['X-Demo-Run-Id'] }
  response: { body: { bytes: 0 }, headers: ['X-Demo-Policy'] }
}

resource appDiagnostic 'Microsoft.ApiManagement/service/diagnostics@2024-05-01' = {
  parent: apim
  name: 'applicationinsights'
  properties: {
    loggerId: logger.id
    alwaysLog: 'allErrors'
    sampling: { samplingType: 'fixed', percentage: 100 }
    frontend: safePipelineLog
    backend: safePipelineLog
    httpCorrelationProtocol: 'W3C'
    verbosity: 'information'
    logClientIp: false
  }
}

resource monitorDiagnostic 'Microsoft.ApiManagement/service/diagnostics@2024-05-01' = {
  parent: apim
  name: 'azuremonitor'
  properties: {
    loggerId: '/loggers/azuremonitor'
    alwaysLog: 'allErrors'
    sampling: { samplingType: 'fixed', percentage: 100 }
    frontend: safePipelineLog
    backend: safePipelineLog
    logClientIp: false
  }
}

resource gatewayLogs 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'gateway-to-workspace'
  scope: apim
  properties: {
    workspaceId: workspace.id
    logAnalyticsDestinationType: 'Dedicated'
    logs: [{ category: 'GatewayLogs', enabled: true }]
  }
}

resource userAgent 'Microsoft.ApiManagement/service/namedValues@2024-05-01' = {
  parent: apim
  name: 'weather-user-agent'
  properties: {
    displayName: 'weather-user-agent'
    value: 'apim-weather-walkthrough (${weatherContact})'
    secret: false
  }
}

resource backendFragment 'Microsoft.ApiManagement/service/policyFragments@2024-05-01' = {
  parent: apim
  name: 'weather-backend'
  properties: {
    description: 'Fixed public upstream; identify requests and remove gateway credentials.'
    format: 'rawxml'
    value: loadTextContent('../policies/fragments/weather-backend.xml')
  }
  dependsOn: [userAgent]
}

resource limitFragment 'Microsoft.ApiManagement/service/policyFragments@2024-05-01' = {
  parent: apim
  name: 'lab-protection'
  properties: {
    description: 'Isolated synthetic lab: intent validation and bounded request rate.'
    format: 'rawxml'
    value: loadTextContent('../policies/fragments/lab-protection.xml')
  }
}

resource responseFragment 'Microsoft.ApiManagement/service/policyFragments@2024-05-01' = {
  parent: apim
  name: 'lab-response'
  properties: {
    description: 'Clearly synthetic response; no upstream calls.'
    format: 'rawxml'
    value: loadTextContent('../policies/fragments/lab-response.xml')
  }
}

resource cors 'Microsoft.ApiManagement/service/policies@2024-05-01' = {
  parent: apim
  name: 'policy'
  properties: {
    format: 'rawxml'
    value: replace(loadTextContent('../policies/global.xml'), '__PORTAL_ORIGIN__', apim.properties.developerPortalUrl)
  }
}

resource weather 'Microsoft.ApiManagement/service/apis@2024-05-01' = {
  parent: apim
  name: 'weather'
  properties: {
    displayName: 'National Weather Service - complete API'
    description: 'Complete Weather.gov API. Live public data through this gateway.'
    path: 'weather'
    protocols: ['https']
    serviceUrl: 'https://api.weather.gov'
    subscriptionRequired: true
    format: 'openapi+json'
    value: loadTextContent('../api/weather.apim.openapi.json')
  }
}

resource weatherPolicy 'Microsoft.ApiManagement/service/apis/policies@2024-05-01' = {
  parent: weather
  name: 'policy'
  properties: {
    format: 'rawxml'
    value: loadTextContent('../policies/weather.xml')
  }
  dependsOn: [backendFragment, cors]
}

resource lab 'Microsoft.ApiManagement/service/apis@2024-05-01' = {
  parent: apim
  name: 'security-lab'
  properties: {
    displayName: 'Security policy lab (synthetic)'
    description: 'Synthetic probe only. Never forwards burst traffic to Weather.gov.'
    path: 'lab'
    protocols: ['https']
    subscriptionRequired: true
  }
}

resource probe 'Microsoft.ApiManagement/service/apis/operations@2024-05-01' = {
  parent: lab
  name: 'probe'
  properties: {
    displayName: 'Synthetic protection probe'
    method: 'GET'
    urlTemplate: '/probe'
    responses: [{ statusCode: 200, description: 'Explicitly synthetic response.' }]
  }
}

resource labPolicy 'Microsoft.ApiManagement/service/apis/policies@2024-05-01' = {
  parent: lab
  name: 'policy'
  properties: {
    format: 'rawxml'
    value: loadTextContent('../policies/lab.xml')
  }
  dependsOn: [probe, limitFragment, responseFragment, cors]
}

resource mcp 'Microsoft.ApiManagement/service/apis@2025-09-01-preview' = {
  parent: apim
  name: 'weather-mcp'
  properties: {
    type: 'mcp'
    displayName: 'Weather tools'
    description: 'Selected read-only tools backed by the complete Weather REST API.'
    path: 'weather-mcp'
    protocols: ['https']
    subscriptionRequired: true
  }
}

var toolDefinitions = [
  { name: 'weather_point', operation: 'point', description: 'Look up a US latitude and longitude to find current forecast office and grid coordinates.' }
  { name: 'weather_forecast', operation: 'gridpoint_forecast', description: 'Get a forecast using wfo, x and y returned by the point lookup. Do not invent grid coordinates.' }
  { name: 'weather_alerts', operation: 'alerts_active_area', description: 'Get active alerts for one US state or area, for example VA. An empty collection means no active alerts.' }
]

resource tools 'Microsoft.ApiManagement/service/apis/tools@2025-09-01-preview' = [for tool in toolDefinitions: {
  parent: mcp
  name: tool.name
  properties: {
    displayName: tool.name
    description: tool.description
    operationId: '/apis/${weather.name}/operations/${tool.operation}'
  }
  dependsOn: [weatherPolicy]
}]

resource mcpPolicy 'Microsoft.ApiManagement/service/apis/policies@2025-09-01-preview' = {
  parent: mcp
  name: 'policy'
  properties: {
    format: 'rawxml'
    value: loadTextContent('../policies/mcp.xml')
  }
  dependsOn: [cors]
}

resource product 'Microsoft.ApiManagement/service/products@2024-05-01' = {
  parent: apim
  name: 'weather-demo'
  properties: {
    displayName: 'Weather developer demo'
    description: 'Weather API, synthetic learning lab, and MCP tools.'
    subscriptionRequired: true
    approvalRequired: true
    subscriptionsLimit: 2
    state: 'published'
  }
}

resource bindings 'Microsoft.ApiManagement/service/products/apis@2024-05-01' = [for apiName in ['weather', 'security-lab', 'weather-mcp']: {
  parent: product
  name: apiName
  dependsOn: [weatherPolicy, labPolicy, mcpPolicy]
}]

resource productGroups 'Microsoft.ApiManagement/service/products/groups@2024-05-01' = [for groupName in ['developers', 'guests']: {
  parent: product
  name: groupName
}]

var tagDefinitions = [
  { name: 'weather', displayName: 'Weather', api: 'weather' }
  { name: 'public-data', displayName: 'Public data', api: 'weather' }
  { name: 'security-lab', displayName: 'Security lab', api: 'security-lab' }
  { name: 'mcp', displayName: 'MCP', api: 'weather-mcp' }
]

resource apiTags 'Microsoft.ApiManagement/service/tags@2024-05-01' = [for tag in tagDefinitions: {
  parent: apim
  name: tag.name
  properties: { displayName: tag.displayName }
}]

resource tagBindings 'Microsoft.ApiManagement/service/apis/tags@2024-05-01' = [for (tag, i) in tagDefinitions: {
  name: '${apim.name}/${tag.api}/${tag.name}'
  dependsOn: [apiTags[i], weather, lab, mcp]
}]

output apimName string = apim.name
output apimId string = apim.id
output gatewayUrl string = apim.properties.gatewayUrl
output portalUrl string = apim.properties.developerPortalUrl
output workspaceId string = workspace.properties.customerId
output insightsName string = insights.name
