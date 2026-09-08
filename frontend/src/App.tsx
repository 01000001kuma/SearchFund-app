import { lazy, Suspense } from "react"
import { BrowserRouter, Routes, Route } from "react-router-dom"
import { Layout } from "@/components/Layout"
import { ErrorBoundary } from "@/components/ErrorBoundary"
import { Loader2 } from "lucide-react"
import { Toaster } from "sonner"

const Dashboard = lazy(() => import("@/pages/Dashboard").then(m => ({ default: m.Dashboard })))
const SearchPage = lazy(() => import("@/pages/SearchPage").then(m => ({ default: m.SearchPage })))
const CompanyDetail = lazy(() => import("@/pages/CompanyDetail").then(m => ({ default: m.CompanyDetail })))
const ListsPage = lazy(() => import("@/pages/ListsPage").then(m => ({ default: m.ListsPage })))
const ChatPage = lazy(() => import("@/pages/ChatPage").then(m => ({ default: m.ChatPage })))
const CandidatesPage = lazy(() => import("@/pages/CandidatesPage").then(m => ({ default: m.CandidatesPage })))

function PageLoader() {
  return (
    <div className="flex items-center justify-center py-20">
      <Loader2 className="size-6 animate-spin text-muted-foreground" />
    </div>
  )
}

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Suspense fallback={<PageLoader />}>
          <Routes>
            <Route element={<Layout />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/candidatas" element={<CandidatesPage />} />
              <Route path="/chat" element={<ChatPage />} />
              <Route path="/buscar" element={<SearchPage />} />
              <Route path="/empresa/:slug" element={<CompanyDetail />} />
              <Route path="/listas" element={<ListsPage />} />
            </Route>
          </Routes>
        </Suspense>
        <Toaster position="top-right" richColors />
      </BrowserRouter>
    </ErrorBoundary>
  )
}
