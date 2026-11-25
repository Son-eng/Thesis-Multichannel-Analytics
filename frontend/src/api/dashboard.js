import { goiApi } from './client.js';

export function layBoLoc(san) {
  return goiApi('GET', `/api/${san}/filters`);
}

export function layKpi(san, tham) {
  return goiApi('GET', `/api/${san}/kpi`, tham);
}

export function layXuHuong(san, tham) {
  return goiApi('GET', `/api/${san}/revenue-trend`, tham);
}

export function layTopSanPham(san, tham) {
  return goiApi('GET', `/api/${san}/top-products`, tham);
}

export function layKenhBan(san, tham) {
  return goiApi('GET', `/api/${san}/by-affiliate`, tham);
}

export function layTheoTinh(san, tham) {
  return goiApi('GET', `/api/${san}/by-province`, tham);
}

export function layTheoGio(san, tham) {
  return goiApi('GET', `/api/${san}/by-hour`, tham);
}

export function layCanhBao(san, tham) {
  return goiApi('GET', `/api/${san}/alerts`, tham);
}
