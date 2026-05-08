import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Middleware to protect dashboard routes.
 * Checks for the accessToken cookie on protected paths.
 * Public paths (/, /login) are allowed without authentication.
 */
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const accessToken = request.cookies.get('accessToken')?.value;

  // Skip middleware for API proxy routes (handled by Next.js rewrites)
  if (pathname.startsWith('/api/')) {
    return NextResponse.next();
  }

  // Public paths that do not require authentication
  const publicPaths = ['/', '/login'];
  const isPublicPath = publicPaths.some(
    (path) => pathname === path || pathname.startsWith('/login'),
  );

  // Allow public paths and static assets
  if (isPublicPath) {
    // If user is already authenticated and trying to access login, redirect to dashboard
    if (pathname.startsWith('/login') && accessToken) {
      return NextResponse.redirect(new URL('/dashboard', request.url));
    }
    return NextResponse.next();
  }

  // Protected routes: redirect to login if no access token
  if (!accessToken) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder assets
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
};
