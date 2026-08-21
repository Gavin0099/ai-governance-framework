import { describe, expect, it, vi } from 'vitest'
import {
    prepareBooksForImportSegment,
    type ImportBook,
} from '../import-logic'
import type { PublisherTrust } from '../trust-engine'

type QueryFilter = { column: string; value: unknown }
type FakeOptions = {
    isbnRows?: any[]
    urlRows?: any[]
    softRows?: any[]
    lookupError?: Error
}

function createFakeSupabase(options: FakeOptions = {}) {
    const rpc = vi.fn()
    const from = vi.fn((table: string) => {
        const filters: QueryFilter[] = []
        const builder: any = {
            select: vi.fn(() => builder),
            in: vi.fn((column: string, value: unknown) => {
                filters.push({ column, value })
                return builder
            }),
            eq: vi.fn((column: string, value: unknown) => {
                filters.push({ column, value })
                return builder
            }),
            then: (resolve: (value: unknown) => unknown, reject?: (reason: unknown) => unknown) => {
                if (table === 'books') return Promise.resolve({ data: [], error: null }).then(resolve, reject)
                if (table !== 'books_master') return Promise.resolve({ data: [], error: null }).then(resolve, reject)
                if (options.lookupError) {
                    return Promise.resolve({ data: null, error: options.lookupError }).then(resolve, reject)
                }
                if (filters.some(filter => filter.column === 'isbn')) {
                    return Promise.resolve({ data: options.isbnRows ?? [], error: null }).then(resolve, reject)
                }
                if (filters.some(filter => filter.column === 'source_url')) {
                    return Promise.resolve({ data: options.urlRows ?? [], error: null }).then(resolve, reject)
                }
                return Promise.resolve({ data: options.softRows ?? [], error: null }).then(resolve, reject)
            },
        }
        return builder
    })

    return { supabase: { from, rpc }, rpc }
}

function makeBook(overrides: Partial<ImportBook> = {}): ImportBook {
    return {
        id: 'pub:9780000000001',
        book_id: 'pub:9780000000001',
        isbn: '9780000000001',
        title: 'Same Book',
        publisher: 'Publisher A',
        original_price: 500,
        price_original: 500,
        price: 450,
        price_sale: 450,
        category: null,
        priority_series: null,
        note: null,
        description: null,
        cover_image: null,
        cover_image_url: null,
        url: null,
        source_url: null,
        publish_date: null,
        core_title: null,
        is_duplicate: false,
        available: true,
        last_seen_at: '2026-07-22T00:00:00Z',
        ...overrides,
    }
}

const publisherTrust: PublisherTrust = {
    publisher_name: 'Publisher A',
    trust_score: 80,
    total_items_processed: 0,
    auto_resolve_count: 0,
    manual_override_count: 0,
}

describe('book import snapshot preparation', () => {
    it('prepares a new master mutation and audit without writing', async () => {
        const { supabase, rpc } = createFakeSupabase()

        const items = await prepareBooksForImportSegment(
            supabase,
            [makeBook()],
            'publisher-id',
            'batch-id',
            publisherTrust,
        )

        expect(items).toEqual([
            expect.objectContaining({
                existing_book_id: null,
                expected_book_updated_at: null,
                write: expect.objectContaining({
                    publisher_id: 'publisher-id',
                    isbn: '9780000000001',
                    title: 'Same Book',
                }),
                audit: expect.objectContaining({
                    action: 'created',
                    source_data: expect.objectContaining({ title: 'Same Book' }),
                }),
            }),
        ])
        expect(rpc).not.toHaveBeenCalled()
    })

    it('captures the existing row version for finalize-time stale-write detection', async () => {
        const existingBook = {
            id: 'master-existing',
            isbn: '9780000000001',
            title: 'Same Book',
            publisher: 'Publisher A',
            series: null,
            source_title: 'Same Book',
            source_price_original: 500,
            list_price: 500,
            available: true,
            updated_at: '2026-07-22T01:02:03Z',
        }
        const { supabase } = createFakeSupabase({ isbnRows: [existingBook] })

        const [item] = await prepareBooksForImportSegment(
            supabase,
            [makeBook()],
            'publisher-id',
            'batch-id',
            publisherTrust,
        )

        expect(item.existing_book_id).toBe('master-existing')
        expect(item.expected_book_updated_at).toBe('2026-07-22T01:02:03Z')
        expect(item.audit).toEqual(expect.objectContaining({ action: 'updated' }))
    })

    it('uses an exact title/publisher/series soft match when stronger keys are absent', async () => {
        const existingBook = {
            id: 'master-soft',
            isbn: null,
            title: 'Same Book',
            publisher: 'Publisher A',
            series: null,
            source_title: 'Same Book',
            source_price_original: 500,
            list_price: 500,
            available: true,
            updated_at: '2026-07-22T02:00:00Z',
        }
        const { supabase } = createFakeSupabase({ softRows: [existingBook] })

        const [item] = await prepareBooksForImportSegment(
            supabase,
            [makeBook({ isbn: '', url: null, source_url: null })],
            'publisher-id',
            'batch-id',
            { ...publisherTrust, trust_score: 95 },
        )

        expect(item.existing_book_id).toBe('master-soft')
        expect(item.audit).toEqual(expect.objectContaining({
            action: 'updated',
            message: 'review_soft_match',
        }))
    })

    it('does not soft-match distinct strong identities to the same existing book', async () => {
        const existingBook = {
            id: 'master-existing',
            isbn: '4710841107252',
            title: '吹奏魔笛的天使：音樂神童莫札特(二版)',
            publisher: 'Publisher A',
            series: null,
            source_title: '吹奏魔笛的天使：音樂神童莫札特(二版)',
            source_url: 'https://example.test/product/000477744',
            source_price_original: 500,
            list_price: 500,
            available: true,
            updated_at: '2026-07-29T00:00:00Z',
        }
        const { supabase } = createFakeSupabase({
            isbnRows: [existingBook],
            softRows: [existingBook],
        })

        const items = await prepareBooksForImportSegment(
            supabase,
            [
                makeBook({
                    isbn: '4710841107252',
                    title: existingBook.title,
                    url: existingBook.source_url,
                    source_url: existingBook.source_url,
                }),
                makeBook({
                    id: 'pub:9789571438214',
                    book_id: 'pub:9789571438214',
                    isbn: '9789571438214',
                    title: existingBook.title,
                    url: 'https://example.test/product/000336937',
                    source_url: 'https://example.test/product/000336937',
                }),
            ],
            'publisher-id',
            'batch-id',
            publisherTrust,
        )

        expect(items[0]).toEqual(expect.objectContaining({
            existing_book_id: 'master-existing',
        }))
        expect(items[1]).toEqual(expect.objectContaining({
            existing_book_id: null,
            audit: expect.objectContaining({ action: 'created' }),
        }))
    })

    it('fails closed before staging when an identity lookup fails', async () => {
        const { supabase, rpc } = createFakeSupabase({
            lookupError: new Error('books_master lookup unavailable'),
        })

        await expect(prepareBooksForImportSegment(
            supabase,
            [makeBook()],
            'publisher-id',
            'batch-id',
            publisherTrust,
        )).rejects.toThrow('books_master lookup unavailable')
        expect(rpc).not.toHaveBeenCalled()
    })
})
