param apimName string
param email string
@secure()
param password string = ''
param createUser bool = true
param createSubscription bool = true

resource apim 'Microsoft.ApiManagement/service@2024-05-01' existing = { name: apimName }

resource developer 'Microsoft.ApiManagement/service/users@2024-05-01' = if (createUser) {
  parent: apim
  name: 'demo-developer'
  properties: {
    email: email
    firstName: 'Demo'
    lastName: 'Developer'
    password: password
    state: 'active'
  }
}

resource subscription 'Microsoft.ApiManagement/service/subscriptions@2024-05-01' = if (createSubscription) {
  parent: apim
  name: 'demo-presenter'
  properties: {
    displayName: 'Seeded presenter subscription'
    scope: '${apim.id}/products/weather-demo'
    ownerId: '${apim.id}/users/demo-developer'
    state: 'active'
    allowTracing: false
  }
  dependsOn: [developer]
}
