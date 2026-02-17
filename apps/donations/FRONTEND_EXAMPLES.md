# Примеры использования API подписок для фронтенда

## 📱 Примеры запросов

### 1. Получение списка пожертвований с подписками

```javascript
// Получение пожертвований текущего пользователя
const fetchDonations = async () => {
  const response = await fetch('https://api.sos-kg.org/api/donations/', {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    }
  });
  
  const data = await response.json();
  return data;
};

// Пример ответа:
// {
//   "results": [
//     {
//       "uuid": "123e4567-e89b-12d3-a456-426614174000",
//       "donation_code": "ABC123XYZ456",
//       "donor_full_name": "Иван Иванов",
//       "amount": "1000.00",
//       "currency": "KGS",
//       "donation_type": "monthly",
//       "status": "completed",
//       "is_recurring": true,
//       "subscription_status": "active",
//       "subscription_status_display": "Активная",
//       "created_at": "2025-11-01T14:23:00Z"
//     }
//   ]
// }
```

### 2. Скачивание квитанции

```javascript
// Скачивание квитанции
const downloadReceipt = async (donationUuid) => {
  const response = await fetch(
    `https://api.sos-kg.org/api/donations/${donationUuid}/download_receipt/`,
    {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    }
  );
  
  if (response.ok) {
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `receipt_${donationUuid}.pdf`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  } else {
    const error = await response.json();
    console.error('Ошибка скачивания:', error.error);
  }
};
```

### 3. Отмена подписки

```javascript
// Отмена подписки
const cancelSubscription = async (donationUuid) => {
  try {
    const response = await fetch(
      `https://api.sos-kg.org/api/donations/${donationUuid}/cancel_subscription/`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json'
        }
      }
    );
    
    if (response.ok) {
      const data = await response.json();
      console.log(data.message); // "Подписка успешно отменена"
      return data;
    } else {
      const error = await response.json();
      throw new Error(error.error);
    }
  } catch (error) {
    console.error('Ошибка отмены подписки:', error);
    throw error;
  }
};
```

### 4. Возобновление подписки

```javascript
// Возобновление подписки
const resumeSubscription = async (donationUuid) => {
  try {
    const response = await fetch(
      `https://api.sos-kg.org/api/donations/${donationUuid}/resume_subscription/`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json'
        }
      }
    );
    
    if (response.ok) {
      const data = await response.json();
      console.log(data.message); // "Подписка успешно возобновлена"
      console.log('Следующий платеж:', data.next_payment_date);
      return data;
    } else {
      const error = await response.json();
      throw new Error(error.error);
    }
  } catch (error) {
    console.error('Ошибка возобновления подписки:', error);
    throw error;
  }
};
```

### 5. Приостановка подписки

```javascript
// Приостановка подписки
const pauseSubscription = async (donationUuid) => {
  try {
    const response = await fetch(
      `https://api.sos-kg.org/api/donations/${donationUuid}/pause_subscription/`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json'
        }
      }
    );
    
    if (response.ok) {
      const data = await response.json();
      console.log(data.message); // "Подписка приостановлена"
      return data;
    } else {
      const error = await response.json();
      throw new Error(error.error);
    }
  } catch (error) {
    console.error('Ошибка приостановки подписки:', error);
    throw error;
  }
};
```

## 🎨 React компоненты (примеры)

### Компонент карточки подписки

```jsx
import React, { useState } from 'react';

const SubscriptionCard = ({ donation }) => {
  const [loading, setLoading] = useState(false);
  
  const getStatusColor = (status) => {
    switch (status) {
      case 'active': return 'green';
      case 'paused': return 'orange';
      case 'cancelled': return 'red';
      case 'pending': return 'blue';
      default: return 'gray';
    }
  };
  
  const handleCancel = async () => {
    if (!confirm('Вы уверены, что хотите отменить подписку?')) return;
    
    setLoading(true);
    try {
      await cancelSubscription(donation.uuid);
      // Обновить данные
      window.location.reload();
    } catch (error) {
      alert('Ошибка отмены подписки: ' + error.message);
    } finally {
      setLoading(false);
    }
  };
  
  const handleResume = async () => {
    setLoading(true);
    try {
      await resumeSubscription(donation.uuid);
      // Обновить данные
      window.location.reload();
    } catch (error) {
      alert('Ошибка возобновления подписки: ' + error.message);
    } finally {
      setLoading(false);
    }
  };
  
  const handleDownloadReceipt = async () => {
    setLoading(true);
    try {
      await downloadReceipt(donation.uuid);
    } catch (error) {
      alert('Ошибка скачивания квитанции: ' + error.message);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="subscription-card">
      <div className="card-header">
        <h3>Подписка {donation.get_donation_type_display}</h3>
        <span 
          className={`status-badge status-${donation.subscription_status}`}
          style={{ color: getStatusColor(donation.subscription_status) }}
        >
          {donation.subscription_status_display}
        </span>
      </div>
      
      <div className="card-body">
        <p><strong>Дата и время:</strong> {new Date(donation.created_at).toLocaleString('ru-RU')}</p>
        <p><strong>Тип:</strong> {donation.get_donation_type_display}</p>
        <p><strong>Сумма:</strong> {donation.amount} {donation.currency}</p>
        <p><strong>Статус:</strong> {donation.get_status_display}</p>
        
        {donation.next_payment_date && (
          <p><strong>Следующий платеж:</strong> {new Date(donation.next_payment_date).toLocaleDateString('ru-RU')}</p>
        )}
      </div>
      
      <div className="card-actions">
        {donation.can_download_receipt && (
          <button 
            onClick={handleDownloadReceipt}
            disabled={loading}
            className="btn btn-primary"
          >
            Скачать квитанцию
          </button>
        )}
        
        {donation.is_recurring && donation.subscription_status === 'active' && (
          <>
            <button 
              onClick={handleCancel}
              disabled={loading}
              className="btn btn-danger"
            >
              Отменить подписку
            </button>
            <button 
              onClick={() => pauseSubscription(donation.uuid)}
              disabled={loading}
              className="btn btn-warning"
            >
              Приостановить
            </button>
          </>
        )}
        
        {donation.is_recurring && ['cancelled', 'paused'].includes(donation.subscription_status) && (
          <button 
            onClick={handleResume}
            disabled={loading}
            className="btn btn-success"
          >
            Возобновить подписку
          </button>
        )}
      </div>
    </div>
  );
};

export default SubscriptionCard;
```

### Компонент списка подписок

```jsx
import React, { useState, useEffect } from 'react';
import SubscriptionCard from './SubscriptionCard';

const SubscriptionList = () => {
  const [donations, setDonations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all'); // all, active, cancelled
  
  useEffect(() => {
    fetchDonations().then(data => {
      setDonations(data.results);
      setLoading(false);
    });
  }, []);
  
  const filteredDonations = donations.filter(donation => {
    if (!donation.is_recurring) return false;
    if (filter === 'all') return true;
    if (filter === 'active') return donation.subscription_status === 'active';
    if (filter === 'cancelled') return donation.subscription_status === 'cancelled';
    return true;
  });
  
  if (loading) return <div>Загрузка...</div>;
  
  return (
    <div className="subscription-list">
      <h2>Подписка и пожертвование</h2>
      
      <div className="filters">
        <button 
          className={filter === 'all' ? 'active' : ''}
          onClick={() => setFilter('all')}
        >
          Все
        </button>
        <button 
          className={filter === 'active' ? 'active' : ''}
          onClick={() => setFilter('active')}
        >
          Активные
        </button>
        <button 
          className={filter === 'cancelled' ? 'active' : ''}
          onClick={() => setFilter('cancelled')}
        >
          Отмененные
        </button>
      </div>
      
      <div className="subscriptions-grid">
        {filteredDonations.map(donation => (
          <SubscriptionCard key={donation.uuid} donation={donation} />
        ))}
      </div>
    </div>
  );
};

export default SubscriptionList;
```

## 🎨 CSS стили (пример)

```css
.subscription-card {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
  background: white;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 15px;
  border-bottom: 1px solid #e0e0e0;
}

.status-badge {
  padding: 5px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: bold;
}

.status-active {
  background-color: #d4edda;
  color: #155724;
}

.status-paused {
  background-color: #fff3cd;
  color: #856404;
}

.status-cancelled {
  background-color: #f8d7da;
  color: #721c24;
}

.status-pending {
  background-color: #d1ecf1;
  color: #0c5460;
}

.card-actions {
  display: flex;
  gap: 10px;
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid #e0e0e0;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background-color: #00A0DC;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: #0088bb;
}

.btn-danger {
  background-color: #dc3545;
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background-color: #c82333;
}

.btn-success {
  background-color: #28a745;
  color: white;
}

.btn-success:hover:not(:disabled) {
  background-color: #218838;
}

.btn-warning {
  background-color: #ffc107;
  color: #212529;
}

.btn-warning:hover:not(:disabled) {
  background-color: #e0a800;
}
```

## 📱 Обработка ошибок

```javascript
// Централизованная обработка ошибок API
const handleApiError = (error) => {
  const errorMessages = {
    'Это не рекуррентное пожертвование': 'Это разовое пожертвование, а не подписка',
    'Подписка уже отменена': 'Подписка уже была отменена ранее',
    'Подписка уже активна': 'Подписка уже активна',
    'Нет прав для отмены этой подписки': 'У вас нет прав для управления этой подпиской',
    'Квитанция будет доступна после обработки платежа': 'Квитанция станет доступна после обработки платежа'
  };
  
  const message = errorMessages[error.message] || error.message || 'Произошла ошибка';
  
  // Можно использовать toast/notification библиотеку
  alert(message);
};

// Использование
try {
  await cancelSubscription(donationUuid);
} catch (error) {
  handleApiError(error);
}
```



