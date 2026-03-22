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

import { RouteRequest, RouteResponse } from '../../core/models/route.model';
import { AInkaufApiPort } from '../../core/ports/api.port';

interface RouteState {
  result: RouteResponse | null;
  loading: boolean;
  error: string | null;
}

const initialState: RouteState = {
  result: null,
  loading: false,
  error: null,
};

export const RouteStore = signalStore(
  { providedIn: 'root' },
  withState(initialState),
  withComputed((state) => ({
    recommendedStore: computed(() => {
      const r = state.result();
      if (!r) return null;
      return r.decisions.find((d) => d.store_id === r.recommended_store_id) ?? null;
    }),
    estimatedTotal: computed(() => state.result()?.estimated_total_eur ?? null),
  })),
  withMethods((store, api = inject(AInkaufApiPort)) => ({
    clearResult(): void {
      patchState(store, { result: null, error: null });
    },
    calculateRoute: rxMethod<RouteRequest>(
      pipe(
        tap(() => patchState(store, { loading: true, error: null })),
        switchMap((req) =>
          api.calculateOptimalRoute(req).pipe(
            tapResponse({
              next: (result) => patchState(store, { result, loading: false }),
              error: (err: { error?: { detail?: string } }) =>
                patchState(store, {
                  loading: false,
                  error: err.error?.detail ?? 'Routenberechnung fehlgeschlagen.',
                }),
            }),
          ),
        ),
      ),
    ),
  })),
);
