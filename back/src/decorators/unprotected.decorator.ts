import { SetMetadata } from '@nestjs/common';

export const IS_PUBLIC_KEY = 'unprotected';
export const unprotected = () => {
  console.log('[DEBUG] @unprotected applied');
  return SetMetadata(IS_PUBLIC_KEY, true);
};
