import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Header from './components/Header'
import MainPage from './pages/MainPage'
import LoginPage from './pages/LoginPage'
import SignupPage from './pages/SignupPage'
import ConstellationFindPage from './pages/ConstellationFindPage'
import ConstellationFindResultPage from './pages/ConstellationFindResultPage'
import ConstellationLocationPage from './pages/ConstellationLocationPage'
import ConstellationInfoPage from './pages/ConstellationInfoPage'
import ConstellationCatalogPage from './pages/ConstellationCatalogPage'
import FortuneReadingPage from './pages/FortuneReadingPage'
import FortuneResultPage from './pages/FortuneResultPage'
import PaymentSuccessPage from './pages/PaymentSuccessPage'
import PaymentCancelPage from './pages/PaymentCancelPage'
import PaymentFailPage from './pages/PaymentFailPage'
import MyPage from './pages/MyPage'
import EditProfilePage from './pages/EditProfilePage'
import { AppContainer, MainContent } from './App.styles'

function App() {
  return (
    <Router>
      <AppContainer>
        <Header />
        <MainContent>
          <Routes>
            <Route path="/" element={<MainPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />
            <Route path="/constellation-find" element={<ConstellationFindPage />} />
            <Route path="/constellation-find-result" element={<ConstellationFindResultPage />} />
            <Route path="/constellation-location" element={<ConstellationLocationPage />} />
            <Route path="/constellation-info" element={<ConstellationInfoPage />} />
            <Route path="/constellation-catalog" element={<ConstellationCatalogPage />} />
            <Route path="/fortune-reading" element={<FortuneReadingPage />} />
            <Route path="/fortune-result" element={<FortuneResultPage />} />
            <Route path="/payment/success" element={<PaymentSuccessPage />} />
            <Route path="/payment/cancel" element={<PaymentCancelPage />} />
            <Route path="/payment/fail" element={<PaymentFailPage />} />
            <Route path="/mypage" element={<MyPage />} />
            <Route path="/edit-profile" element={<EditProfilePage />} />
          </Routes>
        </MainContent>
      </AppContainer>
    </Router>
  )
}

export default App
