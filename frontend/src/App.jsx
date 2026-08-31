import { Route, Routes } from "react-router-dom";
import Navbar from "./components/Navbar";
import Footer from "./components/Footer";
import PrivateRoute from "./components/PrivateRoute";
import AdsList from "./pages/AdsList";
import AdDetail from "./pages/AdDetail";
import CreateAd from "./pages/CreateAd";
import MyAds from "./pages/MyAds";
import MyConnectionRequests from "./pages/MyConnectionRequests";
import ReceivedRequests from "./pages/ReceivedRequests";
import Login from "./pages/Login";
import Register from "./pages/Register";
import PaymentReturn from "./pages/PaymentReturn";

export default function App() {
  return (
    <>
      <Navbar />
      <main className="container">
        <Routes>
          <Route path="/" element={<AdsList />} />
          <Route path="/ads/:id" element={<AdDetail />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route
            path="/ads/new"
            element={
              <PrivateRoute>
                <CreateAd />
              </PrivateRoute>
            }
          />
          <Route
            path="/my-ads"
            element={
              <PrivateRoute>
                <MyAds />
              </PrivateRoute>
            }
          />
          <Route
            path="/my-requests"
            element={
              <PrivateRoute>
                <MyConnectionRequests />
              </PrivateRoute>
            }
          />
          <Route
            path="/received-requests"
            element={
              <PrivateRoute>
                <ReceivedRequests />
              </PrivateRoute>
            }
          />
          <Route
            path="/payments/:id/return"
            element={
              <PrivateRoute>
                <PaymentReturn />
              </PrivateRoute>
            }
          />
        </Routes>
      </main>
      <Footer />
    </>
  );
}
