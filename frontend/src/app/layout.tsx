import type {Metadata} from "next";import "./globals.css";
export const viewport={width:"device-width",initialScale:1,viewportFit:"cover"};
export const metadata:Metadata={title:"Brightloop | Subscription Operations",description:"Manage customers, subscriptions, billing and revenue."};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="en"><body>{children}</body></html>}
