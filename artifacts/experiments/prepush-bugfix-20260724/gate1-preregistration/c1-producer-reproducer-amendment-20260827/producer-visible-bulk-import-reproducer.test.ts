import { NextRequest } from 'next/server'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const fixture = vi.hoisted(() => ({
    captured: [] as Array<Record<string, unknown>>,
    queryResults: [] as Array<{ data: unknown; error: null }>,
}))

vi.mock('@/lib/auth/admin-api', () => ({
    requireAdminApiAccess: vi.fn().mockResolvedValue(null),
}))

vi.mock('@/lib/integration/trust-engine', () => ({
    getPublisherTrust: vi.fn().mockResolvedValue({
        trust_score: 0,
        sample_size: 0,
        source: 'default',
    }),
}))

vi.mock('@/lib/supabase/server', () => ({
    createAdminClient: vi.fn().mockImplementation(async () => {
        const query = () => {
            const chain: Record<string, unknown> = {}
            for (const method of ['select', 'eq', 'in', 'order', 'limit']) {
                chain[method] = vi.fn().mockReturnValue(chain)
            }
            chain.maybeSingle = vi.fn().mockImplementation(async () => fixture.queryResults.shift())
            chain.single = vi.fn().mockImplementation(async () => fixture.queryResults.shift())
            chain.then = (resolve: (value: unknown) => unknown) =>
                Promise.resolve(fixture.queryResults.shift()).then(resolve)
            return chain
        }
        return {
            from: vi.fn().mockImplementation(query),
            rpc: vi.fn().mockImplementation(async (_name: string, args: Record<string, unknown>) => {
                if (Array.isArray(args.p_items)) {
                    fixture.captured = args.p_items as Array<Record<string, unknown>>
                    return { data: { item_count: fixture.captured.length }, error: null }
                }
                if ('p_expected_book_count' in args) {
                    return { data: { batch_id: 'batch-public-1', status: 'staging', warning_count: 0 }, error: null }
                }
                return {
                    data: { expected_chunk_count: 1, finalized: true, persisted_count: 2, received_chunk_count: 1 },
                    error: null,
                }
            }),
        }
    }),
}))

import { POST } from '@/app/api/admin/import-books/route'

describe('public bulk-import identity observation', () => {
    beforeEach(() => {
        fixture.captured = []
        fixture.queryResults = [
            { data: { id: 'publisher-public-1', name: 'Example Publisher', slug: 'example-publisher' }, error: null },
            { data: null, error: null },
            {
                data: [{
                    available: true,
                    id: 'catalog-existing',
                    isbn: '9780000000001',
                    list_price: 100,
                    publisher: 'Example Publisher',
                    series: null,
                    source_price_original: 100,
                    source_title: 'Shared Public Title',
                    source_url: 'https://example.invalid/existing',
                    title: 'Shared Public Title',
                    updated_at: '2026-01-01T00:00:00.000Z',
                }],
                error: null,
            },
            { data: [], error: null },
            {
                data: [{
                    available: true,
                    id: 'catalog-existing',
                    isbn: '9780000000001',
                    list_price: 100,
                    publisher: 'Example Publisher',
                    series: null,
                    source_price_original: 100,
                    source_title: 'Shared Public Title',
                    source_url: 'https://example.invalid/existing',
                    title: 'Shared Public Title',
                    updated_at: '2026-01-01T00:00:00.000Z',
                }],
                error: null,
            },
            { data: [], error: null },
        ]
    })

    it('prints the two public input identities and resulting catalog links', async () => {
        const payload = {
            metadata: {
                book_count: 2,
                publisher: 'example-publisher',
                schema_version: 'bookstore-import.v2',
                snapshot_version: 'public-reproducer-v1',
            },
            books: [
                {
                    available: true,
                    id: 'input-existing',
                    isbn: '9780000000001',
                    last_seen_at: '2026-01-01T00:00:00.000Z',
                    original_price: 100,
                    price: 90,
                    publisher: 'Example Publisher',
                    source_url: 'https://example.invalid/existing',
                    title: 'Shared Public Title',
                },
                {
                    available: true,
                    id: 'input-distinct',
                    isbn: '9780000000002',
                    last_seen_at: '2026-01-01T00:00:00.000Z',
                    original_price: 100,
                    price: 90,
                    publisher: 'Example Publisher',
                    source_url: 'https://example.invalid/distinct',
                    title: 'Shared Public Title',
                },
            ],
        }
        const request = new NextRequest('http://localhost/api/admin/import-books', {
            body: JSON.stringify(payload),
            headers: { 'content-type': 'application/json' },
            method: 'POST',
        })

        const response = await POST(request)
        expect(response.status).toBe(200)
        expect(fixture.captured).toHaveLength(2)

        const observation = {
            input_ids: payload.books.map((book) => book.id),
            linked_catalog_ids: fixture.captured.map((item) => item.existing_book_id),
            schema: 'c1-public-bulk-import-observation.v1',
        }
        console.log(`C1_REPRODUCER_OBSERVATION=${JSON.stringify(observation)}`)
    })
})
