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

import {
  DetourCheckRequest,
  DetourCheckResponse,
} from '../../core/models/detour-check.model';
import { AInkaufApiPort } from '../../core/ports/api.port';

interface DetourState {
  result: DetourCheckResponse | null;
  loading: boolean;
  error: string | null;
}

const initialState: DetourState = {
  result: null,
  loading: false,
  error: null,
};

export const DetourStore = signalStore(
  { providedIn: 'root' },
  withState(initialState),
  withComputed((state) => ({
    isWorthIt: computed(() => state.result()?.is_worth_it ?? null),
    savingsSummary: computed(() => {
      const r = state.result();
      if (!r) return '';
      return r.is_worth_it
        ? `Ersparnis: €${r.net_savings_eur.toFixed(2)}`
        : `Verlust: €${Math.abs(r.net_savings_eur).toFixed(2)}`;
    }),
  })),
  withMethods((store, api = inject(AInkaufApiPort)) => ({
    clearResult(): void {
      patchState(store, { result: null, error: null });
    },
    checkDetour: rxMethod<DetourCheckRequest>(
      pipe(
        tap(() => patchState(store, { loading: true, error: null })),
        switchMap((req) =>
          api.detourCheck(req).pipe(
            tapResponse({
              next: (result) => patchState(store, { result, loading: false }),
              error: (err: { error?: { detail?: string } }) =>
                patchState(store, {
                  loading: false,
                  error: err.error?.detail ?? 'Berechnung fehlgeschlagen.',
                }),
            }),
          ),
        ),
      ),
    ),
  })),
);
