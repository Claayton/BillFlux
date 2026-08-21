import { describe, it, expect } from 'vitest'
import { brl, brdate, brdateShort, maskMoney, moneyToDecimal, toNumber } from '@/utils/format'

describe('toNumber', () => {
  it('devolve NaN para vazio/null/undefined', () => {
    expect(Number.isNaN(toNumber(''))).toBe(true)
    expect(Number.isNaN(toNumber(null))).toBe(true)
    expect(Number.isNaN(toNumber(undefined))).toBe(true)
  })
  it('aceita número', () => {
    expect(toNumber(5)).toBe(5)
    expect(toNumber(5.5)).toBe(5.5)
  })
  it('aceita ponto decimal ("818.45")', () => {
    expect(toNumber('818.45')).toBe(818.45)
  })
  it('aceita formato BR ("1.234,56")', () => {
    expect(toNumber('1.234,56')).toBe(1234.56)
  })
  it('aceita inteiro', () => {
    expect(toNumber('123')).toBe(123)
  })
})

describe('brl', () => {
  it('formata em Real', () => {
    expect(brl(123.43)).toBe('R$\u00a0123,43')
    expect(brl(1000)).toBe('R$\u00a01.000,00')
  })
  it('devolve travessão para valor inválido', () => {
    expect(brl(null)).toBe('—')
    expect(brl('abc')).toBe('—')
  })
})

describe('brdate / brdateShort', () => {
  it('formata dd/mm/aaaa', () => {
    expect(brdate('2026-08-18')).toBe('18/08/2026')
  })
  it('formata data curta', () => {
    expect(brdateShort('2026-08-18')).toBe('18 ago 2026')
  })
  it('devolve travessão para data inválida', () => {
    expect(brdate(null)).toBe('—')
    expect(brdateShort('invalida')).toBe('—')
  })
})

describe('maskMoney', () => {
  it('mascara "15050" como "150,50"', () => {
    expect(maskMoney('15050')).toBe('150,50')
  })
  it('mascara "5" como "0,05"', () => {
    expect(maskMoney('5')).toBe('0,05')
  })
  it('agrupa milhares', () => {
    expect(maskMoney('1234567')).toBe('12.345,67')
  })
  it('devolve vazio para sem dígitos', () => {
    expect(maskMoney('abc')).toBe('')
  })
})

describe('moneyToDecimal', () => {
  it('converte formato BR para decimal', () => {
    expect(moneyToDecimal('150,50')).toBe(150.5)
    expect(moneyToDecimal('1.234,56')).toBe(1234.56)
    expect(moneyToDecimal('0,05')).toBe(0.05)
  })
  it('devolve null para inválido', () => {
    expect(moneyToDecimal(null)).toBe(null)
    expect(moneyToDecimal(undefined)).toBe(null)
    expect(moneyToDecimal('abc')).toBe(null)
  })
})
