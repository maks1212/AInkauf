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

import { ParseResponse } from '../../core/models/parse-item.model';
import { AInkaufApiPort } from '../../core/ports/api.port';

interface NlpState {
  inputText: string;
  result: ParseResponse | null;
  loading: boolean;
  error: string | null;
}

const initialState: NlpState = {
  inputText: '',
  result: null,
  loading: false,
  error: null,
};

export const NlpStore = signalStore(
  { providedIn: 'root' },
  withState(initialState),
  withComputed((state) => ({
    hasResult: computed(() => state.result() !== null),
    formattedResult: computed(() => {
      const r = state.result();
      if (!r) return '';
      return `${r.quantity} ${r.unit} ${r.product_name}`;
    }),
  })),
  withMethods((store, api = inject(AInkaufApiPort)) => ({
    setInputText(text: string): void {
      patchState(store, { inputText: text });
    },
    clearResult(): void {
      patchState(store, { result: null, error: null });
    },
    parseItem: rxMethod<string>(
      pipe(
        tap(() => patchState(store, { loading: true, error: null })),
        switchMap((text) =>
          api.parseItem({ text }).pipe(
            tapResponse({
              next: (result) => patchState(store, { result, loading: false }),
              error: (err: { error?: { detail?: string } }) =>
                patchState(store, {
                  loading: false,
                  error: err.error?.detail ?? 'Parsing fehlgeschlagen.',
                }),
            }),
          ),
        ),
      ),
    ),
  })),
);
