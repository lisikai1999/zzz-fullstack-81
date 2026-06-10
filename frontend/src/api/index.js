import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export function createNetwork(params) {
  return api.post('/networks', params)
}

export function listNetworks() {
  return api.get('/networks')
}

export function getNetwork(id) {
  return api.get(`/networks/${id}`)
}

export function getGraphLayout(id) {
  return api.get(`/networks/${id}/graph_layout`)
}

export function runSimulation(networkId, params) {
  return api.post(`/networks/${networkId}/simulate`, params)
}

export function runSingleSimulation(networkId, params) {
  return api.post(`/networks/${networkId}/simulate_single`, params)
}

export function compareCombinations(networkId, params) {
  return api.post(`/networks/${networkId}/compare`, params)
}

export function getOverlap(networkId) {
  return api.get(`/networks/${networkId}/overlap`)
}

export function optimizeSeeds(networkId, params) {
  return api.post(`/networks/${networkId}/optimize`, params)
}

export function getCommunities(networkId) {
  return api.get(`/networks/${networkId}/communities`)
}
