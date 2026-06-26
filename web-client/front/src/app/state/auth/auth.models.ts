export interface AuthState {
  isAuthenticated: boolean;
  accessToken: string | null;
  refreshToken: string | null;
  user: User | null;
  error: string | null;
  creditAccount?: CreditAccount | null;
}

export interface User {
  createdAt: string;
  deletedAt: string | null;
  email: string;
  firstName: string;
  id: number;
  lastName: string;
  username?: string;
  role: string;
  updatedAt: string;
  creditAccount?: CreditAccount | null;
  // Campos genéricos de perfil
  birthDate?: string | null;
  gender?: string | null;
}

export interface CreditTransaction {
  id: number;
  creditAccountId: number;
  amount: number;
  description?: string | null;
  type?: string | null;
  createdAt: string;
  updatedAt: string | null;
  deletedAt: string | null;
}

export interface CreditAccount {
  id: number;
  userId: number;
  balance: number;
  createdAt: string;
  updatedAt: string | null;
  deletedAt: string | null;
  transactions?: CreditTransaction[];
}

let parsedPersisted: Partial<AuthState> | null = null;
if (typeof window !== 'undefined') {
  try {
    const raw = window.localStorage.getItem('auth');
    if (raw) {
      parsedPersisted = JSON.parse(raw);
    }
  } catch (e) {
    console.warn('Could not parse persisted auth JSON', e);
  }
}

export const initialAuthState: AuthState = parsedPersisted
  ? {
      isAuthenticated: true,
      accessToken: parsedPersisted.accessToken ?? null,
      refreshToken: parsedPersisted.refreshToken ?? null,
      user: parsedPersisted.user ?? null,
      error: null
    }
  : {
      isAuthenticated: false,
      accessToken: null,
      refreshToken: null,
      user: null,
      error: null
    };
