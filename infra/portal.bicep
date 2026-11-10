param apimName string
param revision string = 'seed-v1'

resource apim 'Microsoft.ApiManagement/service@2024-05-01' existing = { name: apimName }

resource portal 'Microsoft.ApiManagement/service/portalRevisions@2024-05-01' = {
  parent: apim
  name: revision
  properties: {
    description: 'Default managed portal for the Weather developer demo.'
    isCurrent: true
  }
}
