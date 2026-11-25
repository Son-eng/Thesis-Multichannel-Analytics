import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// Mọi màu phải khai báo trong src/theme/tokens.js; test này quét src/ để chặn mã hex ở chỗ khác.

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
    const mau = '#' + 'ABCDEF';
    expect(('color: ' + mau + ';').match(MAU_HEX)).toHaveLength(1);
    expect(('x ' + mau).match(MAU_HEX)).toHaveLength(1);
    expect('href="#"'.match(MAU_HEX)).toBeNull();
  });
});
