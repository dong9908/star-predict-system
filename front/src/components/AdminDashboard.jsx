import { useState, useEffect } from 'react'
import { adminStyles as styles } from './styles/AdminDashboard.js'

function AdminDashboard() {
  const [activeTab, setActiveTab] = useState('users') // 'users' 또는 'payments'
  const [users, setUsers] = useState([])
  const [payments, setPayments] = useState([])
  const [loading, setLoading] = useState(true)

  const fetchAdminData = async () => {
    try {
      const token = localStorage.getItem('accessToken')
      const requestOptions = {
        headers: {
          Authorization: `Bearer ${token}`
        }
      }

      // 1. 회원 목록 조회 API 호출
      const userRes = await fetch('http://127.0.0.1:8000/api/admin/users', requestOptions)
      if (userRes.ok) {
        const userData = await userRes.json()
        setUsers(userData)
      }

      // 2. 카카오페이 결제 내역 조회 API 호출
      const payRes = await fetch('http://127.0.0.1:8000/api/admin/payments', requestOptions)
      if (payRes.ok) {
        const payData = await payRes.json()
        setPayments(payData)
      }
    } catch (error) {
      console.error('관리자 데이터를 불러오는데 실패했습니다.', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAdminData()
  }, [])

  // 사용자 탈퇴(삭제) 핸들러
  const handleDeleteUser = async (userId, userEmail) => {
    if (!window.confirm(`정말 [${userEmail}] 회원을 탈퇴(삭제)시키겠습니까?`)) {
      return
    }

    try {
      const token = localStorage.getItem('accessToken')
      const res = await fetch(`http://127.0.0.1:8000/api/admin/users/${userId}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`
        }
      })

      if (res.ok) {
        alert('성공적으로 탈퇴 처리되었습니다.')
        fetchAdminData()
      } else {
        const errData = await res.json()
        alert(`탈퇴 처리 실패: ${errData.detail || '알 수 없는 오류'}`)
      }
    } catch (error) {
      console.error('회원 탈퇴 처리 중 에러 발생:', error)
      alert('회원 탈퇴 처리 중 오류가 발생했습니다.')
    }
  }

  if (loading) {
    return <div style={styles.loading}>관리자 데이터를 불러오는 중...</div>
  }

  return (
    <div style={styles.container}>
      {/* 상단 타이틀 영역 */}
      <div style={styles.headerArea}>
        <h1 style={styles.title}>관리자 대시보드</h1>
        <p style={styles.subtitle}>회원 정보 및 카카오페이 결제 내역을 통합 관리합니다.</p>
      </div>

      {/* 탭 전환 버튼 영역 */}
      <div style={styles.tabsArea}>
        <button
          onClick={() => setActiveTab('users')}
          style={{
            ...styles.tabBtn,
            background: activeTab === 'users' ? '#9333ea' : '#1e293b'
          }}
        >
          회원 목록 관리 ({users.length})
        </button>
        <button
          onClick={() => setActiveTab('payments')}
          style={{
            ...styles.tabBtn,
            background: activeTab === 'payments' ? '#9333ea' : '#1e293b'
          }}
        >
          카카오페이 결제 내역 ({payments.length})
        </button>
      </div>

      {/* 컨텐츠 박스 영역 */}
      <div style={styles.contentArea}>
        {/* 탭 1: 회원 목록 테이블 */}
        {activeTab === 'users' && (
          <div style={styles.card}>
            <h3 style={styles.cardTitle}>가입된 회원 목록</h3>
            <table style={styles.table}>
              <thead>
                <tr style={styles.tableHeaderRow}>
                  <th style={{ padding: '1rem', width: '15%' }}>ID</th>
                  <th style={{ padding: '1rem', width: '40%' }}>이메일</th>
                  <th style={{ padding: '1rem', width: '30%' }}>이름</th>
                  <th style={{ padding: '1rem', width: '15%', textAlign: 'center' }}>관리</th>
                </tr>
              </thead>
              <tbody>
                {users.length === 0 ? (
                  <tr>
                    <td colSpan="4" style={styles.emptyCell}>
                      등록된 회원이 없습니다.
                    </td>
                  </tr>
                ) : (
                  users.map(u => (
                    <tr key={u.user_id} style={styles.tableRow}>
                      <td style={styles.td}>{u.user_id}</td>
                      <td style={styles.td}>{u.email}</td>
                      <td style={styles.td}>{u.name}</td>
                      <td style={{ ...styles.td, textAlign: 'center' }}>
                        <button
                          onClick={() => handleDeleteUser(u.user_id, u.email)}
                          style={styles.deleteBtn}
                        >
                          강제 탈퇴
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* 탭 2: 카카오페이 결제 내역 테이블 */}
        {activeTab === 'payments' && (
          <div style={styles.card}>
            <h3 style={styles.cardTitle}>카카오페이 결제 내역</h3>
            <table style={styles.table}>
              <thead>
                <tr style={styles.tableHeaderRow}>
                  <th style={styles.th}>결제 고유번호(TID)</th>
                  <th style={styles.th}>회원 ID</th>
                  <th style={styles.th}>상품명</th>
                  <th style={styles.th}>결제 금액</th>
                  <th style={styles.th}>상태</th>
                  <th style={styles.th}>결제 일시</th>
                </tr>
              </thead>
              <tbody>
                {payments.length === 0 ? (
                  <tr>
                    <td colSpan="6" style={styles.emptyCell}>
                      결제 내역이 없습니다.
                    </td>
                  </tr>
                ) : (
                  payments.map(p => (
                    <tr key={p.tid} style={styles.tableRow}>
                      <td style={{ ...styles.td, fontSize: '0.85rem', color: '#94a3b8' }}>{p.tid}</td>
                      <td style={styles.td}>{p.user_id}</td>
                      <td style={styles.td}>{p.item_name}</td>
                      <td style={{ ...styles.td, color: '#34d399', fontWeight: '600' }}>{p.total_amount?.toLocaleString()}원</td>
                      <td style={styles.td}>{p.status}</td>
                      <td style={{ ...styles.td, color: '#94a3b8' }}>{p.created_at || '-'}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

export default AdminDashboard