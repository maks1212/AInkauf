import { computed, inject } from '@angular/core';
import {
  signalStore,
  withState,
  withComputed,
  withMethods,
  patchState,
} from '@ngrx/signals';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { pipe, switchMap, tap } from 'rxjs';
import { tapResponse } from '@ngrx/operators';

import { PriceRecord } from '../../core/models/price.model';
import { AInkaufApiPort } from '../../core/ports/api.port';

interface PriceState {
  records: PriceRecord[];
  loading: boolean;
  error: string | null;
}

const initialState: PriceState = {
  records: [],
  loading: false,
  error: null,
};

export const PriceStore = signalStore(
  { providedIn: 'root' },
  withState(initialState),
  withComputed((state) => ({
    recordCount: computed(() => state.records().length),
    cheapestByProduct: computed(() => {
      const records = state.records();
      const grouped = new Map<string, PriceRecord>();
      for (const r of records) {
        const existing = grouped.get(r.product_key);
        if (!existing || r.price_eur < existing.price_eur) {
          grouped.set(r.product_key, r);
        }
      }
      return [...grouped.values()];
    }),
  })),
  withMethods((store, api = inject(AInkaufApiPort)) => ({
    loadPrices: rxMethod<void>(
      pipe(
        tap(() => patchState(store, { loading: true, error: null })),
        switchMap(() =>
          api.fetchPrices().pipe(
            tapResponse({
              next: (res) => patchState(store, { records: res.items, loading: false }),
              error: () =>
                patchState(store, {
                  loading: false,
                  error: 'Preise konnten nicht geladen werden.',
                }),
            }),
          ),
        ),
      ),
    ),
  })),
);
