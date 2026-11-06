import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// Mọi màu phải khai báo trong src/theme/tokens.js. Test này quét src/ (trừ src/theme/) và báo lỗi
// nếu thấy mã màu hex (#RGB, #RRGGBB, #RRGGBBAA) ở bất kỳ file nào, kể cả file test.

const thuMucSrc = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const MAU_HEX = /#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![0-9a-zA-Z])/g;

function lietKeFile(thuMuc) {
  const kq = [];
  fs.readdirSync(thuMuc, { withFileTypes: true }).forEach((muc) => {
    const duongDan = path.join(thuMuc, muc.name);
    if (muc.isDirectory()) {
      if (muc.name !== 'theme') {
        kq.push(...lietKeFile(duongDan));
      }
    } else if (/\.(js|jsx|css|html)$/.test(muc.name)) {
      kq.push(duongDan);
    }
  });
  return kq;
}

describe('không có mã màu hex ngoài src/theme/', () => {
  it('quét toàn bộ src/', () => {
    const viPham = [];
    lietKeFile(thuMucSrc).forEach((file) => {
      const noiDung = fs.readFileSync(file, 'utf8');
      const khop = noiDung.match(MAU_HEX);
      if (khop) {
        viPham.push(`${path.relative(thuMucSrc, file)}: ${khop.join(', ')}`);
      }
    });
    expect(viPham).toEqual([]);
  });

  it('bộ quét thật sự bắt được mã hex (không quét hụt)', () => {
    // Dựng chuỗi mã màu tại chỗ để chính file này không chứa mã hex nguyên văn.
    const mau = '#' + 'ABCDEF';
    expect(('color: ' + mau + ';').match(MAU_HEX)).toHaveLength(1);
    expect(('x ' + mau).match(MAU_HEX)).toHaveLength(1);
    expect('href="#"'.match(MAU_HEX)).toBeNull();
  });
});
