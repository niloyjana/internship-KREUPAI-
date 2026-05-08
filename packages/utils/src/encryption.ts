import { createCipheriv, createDecipheriv, randomBytes, scryptSync } from 'crypto';

const ALGORITHM = 'aes-256-gcm';
const IV_LENGTH = 16; // 128 bits
const AUTH_TAG_LENGTH = 16; // 128 bits
const SALT_LENGTH = 32;
const KEY_LENGTH = 32; // 256 bits

/**
 * Derives a 256-bit key from the provided passphrase using scrypt.
 */
function deriveKey(key: string, salt: Buffer): Buffer {
  return scryptSync(key, salt, KEY_LENGTH);
}

/**
 * Encrypts a plaintext string using AES-256-GCM.
 *
 * The output format is: base64(salt + iv + authTag + ciphertext)
 *
 * @param text - The plaintext to encrypt
 * @param key - The encryption key (passphrase)
 * @returns The encrypted string in base64 format
 */
export function encrypt(text: string, key: string): string {
  const salt = randomBytes(SALT_LENGTH);
  const derivedKey = deriveKey(key, salt);
  const iv = randomBytes(IV_LENGTH);

  const cipher = createCipheriv(ALGORITHM, derivedKey, iv);
  const encrypted = Buffer.concat([
    cipher.update(text, 'utf8'),
    cipher.final(),
  ]);
  const authTag = cipher.getAuthTag();

  // Combine: salt + iv + authTag + ciphertext
  const combined = Buffer.concat([salt, iv, authTag, encrypted]);
  return combined.toString('base64');
}

/**
 * Decrypts an AES-256-GCM encrypted string.
 *
 * @param ciphertext - The encrypted string in base64 format (as produced by encrypt)
 * @param key - The encryption key (passphrase)
 * @returns The decrypted plaintext string
 */
export function decrypt(ciphertext: string, key: string): string {
  const combined = Buffer.from(ciphertext, 'base64');

  // Extract components
  const salt = combined.subarray(0, SALT_LENGTH);
  const iv = combined.subarray(SALT_LENGTH, SALT_LENGTH + IV_LENGTH);
  const authTag = combined.subarray(
    SALT_LENGTH + IV_LENGTH,
    SALT_LENGTH + IV_LENGTH + AUTH_TAG_LENGTH,
  );
  const encrypted = combined.subarray(
    SALT_LENGTH + IV_LENGTH + AUTH_TAG_LENGTH,
  );

  const derivedKey = deriveKey(key, salt);

  const decipher = createDecipheriv(ALGORITHM, derivedKey, iv);
  decipher.setAuthTag(authTag);

  const decrypted = Buffer.concat([
    decipher.update(encrypted),
    decipher.final(),
  ]);

  return decrypted.toString('utf8');
}
