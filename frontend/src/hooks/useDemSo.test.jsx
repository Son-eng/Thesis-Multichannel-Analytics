import { describe, it, expect, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useDemSo, lamMuot } from './useDemSo.js';

describe('useDemSo', () => {
  it('chuyển động tắt (tat: true): trả NGAY giá trị cuối, không đếm', () => {
    const { result } = renderHook(() => useDemSo(840035154, { tat: true }));
    expect(result.current).toBe(840035154);
  });

  it('hệ điều hành bật giảm chuyển động: trả ngay giá trị cuối', () => {
    window.matchMedia = (truyVan) => ({ matches: truyVan.includes('reduce'), media: truyVan, addEventListener() {}, removeEventListener() {} });
    const { result } = renderHook(() => useDemSo(1234));
    expect(result.current).toBe(1234);
  });

  it('giá trị null không bao giờ thành 0 (quy tắc 1)', () => {
    const { result } = renderHook(() => useDemSo(null, { tat: true }));
    expect(result.current).toBeNull();
    // Cả khi chuyển động bật: null chưa bao giờ biến thành 0 ở giá trị cuối.
    window.matchMedia = (truyVan) => ({ matches: false, media: truyVan, addEventListener() {}, removeEventListener() {} });
    const { result: r2 } = renderHook(() => useDemSo(null));
    expect(r2.current).toBeNull();
  });

  it('bật chuyển động: bắt đầu từ 0 rồi tiến dần đến giá trị cuối', () => {
    window.matchMedia = (truyVan) => ({ matches: false, media: truyVan, addEventListener() {}, removeEventListener() {} });
    vi.useFakeTimers();
    let thoiGian = 0;
    const raf = vi.spyOn(window, 'requestAnimationFrame').mockImplementation((cb) => setTimeout(() => cb((thoiGian += 100)), 100));
    vi.spyOn(window, 'cancelAnimationFrame').mockImplementation((id) => clearTimeout(id));
    const { result } = renderHook(() => useDemSo(1000));
    expect(result.current).toBe(0);
    act(() => {
      vi.advanceTimersByTime(300);
    });
    expect(result.current).toBeGreaterThan(0);
    expect(result.current).toBeLessThan(1000 + 1);
    act(() => {
      vi.advanceTimersByTime(3000);
    });
    expect(result.current).toBe(1000);
    raf.mockRestore();
  });

  it('đổi giá trị đích: chạy từ giá trị hiện tại, không chạy lại từ 0', () => {
    window.matchMedia = (truyVan) => ({ matches: false, media: truyVan, addEventListener() {}, removeEventListener() {} });
    vi.useFakeTimers();
    let thoiGian = 0;
    vi.spyOn(window, 'requestAnimationFrame').mockImplementation((cb) => setTimeout(() => cb((thoiGian += 100)), 100));
    vi.spyOn(window, 'cancelAnimationFrame').mockImplementation((id) => clearTimeout(id));
    const { result, rerender } = renderHook(({ dich }) => useDemSo(dich), { initialProps: { dich: 1000 } });
    act(() => {
      vi.advanceTimersByTime(3000);
    });
    expect(result.current).toBe(1000);
    rerender({ dich: 2000 });
    act(() => {
      vi.advanceTimersByTime(100);
    });
    expect(result.current).toBeGreaterThanOrEqual(1000);
    act(() => {
      vi.advanceTimersByTime(3000);
    });
    expect(result.current).toBe(2000);
  });

  it('hàm làm mượt: 0 -> 0, 1 -> 1, tăng dần', () => {
    expect(lamMuot(0)).toBeCloseTo(0.0, 2);
    expect(lamMuot(1)).toBe(1);
    expect(lamMuot(0.5)).toBeGreaterThan(0.9);
  });
});
