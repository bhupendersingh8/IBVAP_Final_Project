import React from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";

export const Layout: React.FC = () => {
  return (
    <div className="min-h-screen bg-background text-on-surface antialiased flex flex-col font-body-md">
      <Sidebar />
      <div className="pl-72 flex flex-col min-h-screen">
        <Header />
        <main className="w-full pt-16 bg-background flex-1 px-space-lg py-space-lg">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
