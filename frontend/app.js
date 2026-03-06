const { useState, useEffect, createContext, useContext } = React;

// --- API Configuration ---
const api = axios.create({
    baseURL: 'http://localhost:8000',
});

// Add token to requests if available
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// --- Auth Context ---
const AuthContext = createContext(null);

const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const checkAuth = async () => {
            const token = localStorage.getItem('token');
            if (token) {
                try {
                    const res = await api.get('/auth/me');
                    setUser(res.data);
                } catch (err) {
                    console.error("Auth check failed", err);
                    localStorage.removeItem('token');
                }
            }
            setLoading(false);
        };
        checkAuth();
    }, []);

    const login = async (email, password) => {
        const formData = new FormData(); // FastAPI OAuth2 expects form data strictly? No, our schema is JSON
        // Wait, our backend expects JSON for /auth/login based on schema? 
        // Let's check schemas.UserLogin. It's a Pydantic model, so JSON body is expected.
        const res = await api.post('/auth/login', { email, password });
        localStorage.setItem('token', res.data.access_token);
        setUser(res.data.user);
    };

    const register = async (userData) => {
        const res = await api.post('/auth/register', userData);
        localStorage.setItem('token', res.data.access_token);
        setUser(res.data.user);
    };

    const logout = () => {
        localStorage.removeItem('token');
        setUser(null);
    };

    return (
        <AuthContext.Provider value={{ user, login, register, logout, loading }}>
            {children}
        </AuthContext.Provider>
    );
};

const useAuth = () => useContext(AuthContext);

// --- Components ---

const Navbar = ({ setPage }) => {
    const { user, logout } = useAuth();
    return (
        <nav className="glass-panel sticky top-0 z-50 shadow-sm border-b border-white/20">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex justify-between h-16">
                    <div className="flex cursor-pointer items-center" onClick={() => setPage('home')}>
                        <span className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-primary-dark">
                            ElectroRecover
                        </span>
                    </div>
                    <div className="flex items-center space-x-4">
                        <button onClick={() => setPage('home')} className="text-slate-600 hover:text-primary font-medium transition-colors">Browse</button>
                        {user ? (
                            <>
                                <button onClick={() => setPage('create-listing')} className="btn-animated bg-primary text-white px-5 py-2 rounded-full font-medium hover:bg-primary-dark shadow-lg shadow-primary/30">
                                    + Sell Item
                                </button>
                                <button onClick={() => setPage('dashboard')} className="text-slate-600 hover:text-primary font-medium transition-colors">Dashboard</button>
                                {user.role === 'admin' && (
                                    <button onClick={() => setPage('admin')} className="text-purple-600 hover:text-purple-800 font-bold">Admin</button>
                                )}
                                <div className="flex items-center space-x-3 border-l pl-4 ml-4 border-slate-200">
                                    <span className="text-sm font-medium text-slate-500">Hi, {user.name}</span>
                                    <button onClick={logout} className="text-sm text-red-500 hover:text-red-700 font-medium">Logout</button>
                                </div>
                            </>
                        ) : (
                            <>
                                <button onClick={() => setPage('login')} className="text-slate-600 hover:text-primary font-medium transition-colors">Login</button>
                                <button onClick={() => setPage('register')} className="btn-animated bg-slate-900 text-white px-5 py-2 rounded-full font-medium hover:bg-slate-800 shadow-lg">
                                    Register
                                </button>
                            </>
                        )}
                    </div>
                </div>
            </div>
        </nav>
    );
};

const ListingCard = ({ listing, onRequest }) => {
    return (
        <div className="btn-animated bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden hover:shadow-xl group">
            <div className="h-48 bg-slate-100 flex items-center justify-center relative overflow-hidden">
                {listing.photos && listing.photos.length > 0 ? (
                    <img src={listing.photos[0]} alt={listing.title} className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-110" />
                ) : (
                    <div className="text-slate-300 flex flex-col items-center">
                        <span className="text-4xl mb-2">📷</span>
                        <span className="text-sm font-medium">No Image</span>
                    </div>
                )}
                <div className="absolute top-3 right-3">
                    <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider shadow-sm ${listing.status === 'active' ? 'bg-green-500 text-white' : 'bg-slate-500 text-white'}`}>
                        {listing.status}
                    </span>
                </div>
            </div>
            <div className="p-5">
                <div className="flex justify-between items-start mb-2">
                    <span className="inline-block px-3 py-1 rounded-full text-xs font-semibold bg-primary/10 text-primary">
                        {listing.category}
                    </span>
                    <span className="text-xl font-bold text-slate-900">${listing.price}</span>
                </div>

                <h3 className="text-lg font-bold text-slate-800 mb-1 group-hover:text-primary transition-colors">{listing.title}</h3>
                <p className="text-sm text-slate-500 mb-4">{listing.brand} • {listing.model}</p>

                <div className="space-y-2 mb-4">
                    <div className="flex items-center text-sm">
                        <span className="text-slate-400 w-20">Condition:</span>
                        <span className={`font-medium ${listing.condition === 'broken' ? 'text-red-500' : 'text-green-500'}`}>
                            {listing.condition.replace('_', ' ').toUpperCase()}
                        </span>
                    </div>
                    <div className="flex items-center text-sm">
                        <span className="text-slate-400 w-20">Location:</span>
                        <span className="text-slate-600 truncate">{listing.location}</span>
                    </div>
                </div>

                {listing.status === 'active' && (
                    <button
                        onClick={() => onRequest(listing.id)}
                        className="w-full btn-animated py-2.5 rounded-xl border-2 border-primary text-primary font-bold hover:bg-primary hover:text-white transition-all"
                    >
                        Request to Buy
                    </button>
                )}
            </div>
        </div>
    );
};

// --- Pages ---

const HomePage = ({ setPage }) => {
    const [listings, setListings] = useState([]);
    const [filters, setFilters] = useState({ category: '', condition: '' });

    useEffect(() => {
        fetchListings();
    }, [filters]);

    const fetchListings = async () => {
        try {
            const params = {};
            if (filters.category) params.category = filters.category;
            if (filters.condition) params.condition = filters.condition;

            const res = await api.get('/listings/', { params });
            setListings(res.data);
        } catch (err) {
            console.error("Failed to fetch listings", err);
        }
    };

    const handleBuyRequest = async (listingId) => {
        try {
            await api.post('/requests/', { listing_id: listingId });
            alert("Buy request sent successfully! Check your dashboard.");
        } catch (err) {
            alert(err.response?.data?.detail || "Failed to send request. You might need to login.");
            if (err.response?.status === 401) setPage('login');
        }
    };

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="flex gap-8">
                {/* Sidebar Filters */}
                <div className="w-64 flex-shrink-0">
                    <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
                        <h3 className="font-semibold text-gray-900 mb-4">Filters</h3>

                        <div className="mb-4">
                            <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                            <input
                                type="text"
                                className="w-full border-gray-300 rounded-md shadow-sm p-2 border"
                                placeholder="e.g. Phone, Laptop"
                                value={filters.category}
                                onChange={e => setFilters({ ...filters, category: e.target.value })}
                            />
                        </div>

                        <div className="mb-4">
                            <label className="block text-sm font-medium text-gray-700 mb-1">Condition</label>
                            <select
                                className="w-full border-gray-300 rounded-md shadow-sm p-2 border"
                                value={filters.condition}
                                onChange={e => setFilters({ ...filters, condition: e.target.value })}
                            >
                                <option value="">All</option>
                                <option value="broken">Broken</option>
                                <option value="for_parts">For Parts</option>
                                <option value="used">Used</option>
                                <option value="new">New</option>
                            </select>
                        </div>
                    </div>
                </div>

                {/* Listing Grid */}
                <div className="flex-1">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {listings.map(listing => (
                            <ListingCard key={listing.id} listing={listing} onRequest={handleBuyRequest} />
                        ))}
                    </div>
                    {listings.length === 0 && (
                        <div className="text-center py-12 text-gray-500">
                            No listings found matching your criteria.
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

const LoginPage = ({ setPage }) => {
    const { login } = useAuth();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            await login(email, password);
            setPage('home');
        } catch (err) {
            setError(err.response?.data?.detail || 'Login failed');
        }
    };

    return (
        <div className="min-h-[80vh] flex items-center justify-center p-4">
            <div className="glass-panel p-8 rounded-2xl shadow-xl w-full max-w-md animate-[float_6s_ease-in-out_infinite]">
                <h2 className="text-3xl font-bold mb-6 text-center text-slate-800">Welcome Back</h2>
                {error && <div className="bg-red-50 text-red-600 p-3 rounded-lg mb-4 text-sm border border-red-100">{error}</div>}

                <form onSubmit={handleSubmit} className="space-y-5">
                    <div>
                        <label className="block text-sm font-medium text-slate-600 mb-1">Email Address</label>
                        <input
                            type="email"
                            required
                            className="w-full rounded-lg border-gray-300 shadow-sm focus:border-primary focus:ring-primary p-3 transition-all"
                            value={email}
                            onChange={e => setEmail(e.target.value)}
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-600 mb-1">Password</label>
                        <input
                            type="password"
                            required
                            className="w-full rounded-lg border-gray-300 shadow-sm focus:border-primary focus:ring-primary p-3 transition-all"
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                        />
                    </div>
                    <button type="submit" className="w-full btn-animated bg-primary text-white py-3 rounded-xl font-bold hover:bg-primary-dark shadow-lg shadow-primary/30">
                        Sign In
                    </button>
                </form>
                <div className="mt-6 text-center text-sm text-slate-500">
                    New here? <button onClick={() => setPage('register')} className="text-primary font-bold hover:underline">Create an account</button>
                </div>
            </div>
        </div>
    );
};

const RegisterPage = ({ setPage }) => {
    const { register } = useAuth();
    const [formData, setFormData] = useState({ name: '', email: '', password: '', role: 'buyer', location: '', phone: '' });
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            await register(formData);
            setPage('home');
        } catch (err) {
            setError(err.response?.data?.detail || 'Registration failed');
        }
    };

    return (
        <div className="min-h-[80vh] flex items-center justify-center py-12 p-4">
            <div className="glass-panel p-8 rounded-2xl shadow-xl w-full max-w-md">
                <h2 className="text-3xl font-bold mb-6 text-center text-slate-800">Join the Market</h2>
                {error && <div className="bg-red-50 text-red-600 p-3 rounded-lg mb-4 text-sm border border-red-100">{error}</div>}

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-slate-600 mb-1">Full Name</label>
                        <input
                            type="text"
                            required
                            className="w-full rounded-lg border-gray-300 shadow-sm focus:border-primary focus:ring-primary p-3"
                            value={formData.name}
                            onChange={e => setFormData({ ...formData, name: e.target.value })}
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-600 mb-1">Email</label>
                        <input
                            type="email"
                            required
                            className="w-full rounded-lg border-gray-300 shadow-sm focus:border-primary focus:ring-primary p-3"
                            value={formData.email}
                            onChange={e => setFormData({ ...formData, email: e.target.value })}
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-600 mb-1">Phone Number (for WhatsApp)</label>
                        <input
                            type="tel"
                            required
                            placeholder="+91 9876543210"
                            className="w-full rounded-lg border-gray-300 shadow-sm focus:border-primary focus:ring-primary p-3"
                            value={formData.phone}
                            onChange={e => setFormData({ ...formData, phone: e.target.value })}
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-600 mb-1">Password</label>
                        <input
                            type="password"
                            required
                            className="w-full rounded-lg border-gray-300 shadow-sm focus:border-primary focus:ring-primary p-3"
                            value={formData.password}
                            onChange={e => setFormData({ ...formData, password: e.target.value })}
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-600 mb-1">I want to</label>
                        <select
                            className="w-full rounded-lg border-gray-300 shadow-sm focus:border-primary focus:ring-primary p-3"
                            value={formData.role}
                            onChange={e => setFormData({ ...formData, role: e.target.value })}
                        >
                            <option value="buyer">Buy Parts & Devices</option>
                            <option value="seller">Sell Broken Items</option>
                        </select>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-600 mb-1">Location</label>
                        <input
                            type="text"
                            required
                            className="w-full rounded-lg border-gray-300 shadow-sm focus:border-primary focus:ring-primary p-3"
                            value={formData.location}
                            onChange={e => setFormData({ ...formData, location: e.target.value })}
                        />
                    </div>
                    <button type="submit" className="w-full btn-animated bg-primary text-white py-3 rounded-xl font-bold hover:bg-primary-dark shadow-lg shadow-primary/30 mt-2">
                        Create Account
                    </button>
                </form>
                <div className="mt-6 text-center text-sm text-slate-500">
                    Already a member? <button onClick={() => setPage('login')} className="text-primary font-bold hover:underline">Log in</button>
                </div>
            </div>
        </div>
    );
};

const CreateListingPage = ({ setPage }) => {
    const [formData, setFormData] = useState({
        title: '', category: '', brand: '', model: '',
        condition: 'broken', price: '', location: '', description: '',
        working_parts: ''
    });

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            await api.post('/listings/', {
                ...formData,
                price: parseFloat(formData.price),
                photos: [] // Placeholder for now
            });
            alert('Listing created!');
            setPage('dashboard');
        } catch (err) {
            alert('Failed to create listing: ' + (err.response?.data?.detail || err.message));
        }
    };

    return (
        <div className="max-w-2xl mx-auto py-8 px-4">
            <h1 className="text-2xl font-bold mb-6">Create New Listing</h1>
            <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 space-y-4">
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700">Category</label>
                        <input type="text" required className="w-full border p-2 rounded" placeholder="Smartphone"
                            value={formData.category} onChange={e => setFormData({ ...formData, category: e.target.value })} />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700">Brand</label>
                        <input type="text" className="w-full border p-2 rounded" placeholder="Apple"
                            value={formData.brand} onChange={e => setFormData({ ...formData, brand: e.target.value })} />
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700">Model</label>
                        <input type="text" className="w-full border p-2 rounded" placeholder="iPhone 12"
                            value={formData.model} onChange={e => setFormData({ ...formData, model: e.target.value })} />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700">Condition</label>
                        <select className="w-full border p-2 rounded"
                            value={formData.condition} onChange={e => setFormData({ ...formData, condition: e.target.value })}>
                            <option value="broken">Broken / Damaged</option>
                            <option value="for_parts">For Parts Only</option>
                            <option value="used">Used / Working</option>
                        </select>
                    </div>
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700">Title</label>
                    <input type="text" required className="w-full border p-2 rounded" placeholder="Broken Screen iPhone 12 Pro Max"
                        value={formData.title} onChange={e => setFormData({ ...formData, title: e.target.value })} />
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700">Working Parts (if any)</label>
                    <textarea className="w-full border p-2 rounded" placeholder="Motherboard, Battery seem fine..."
                        value={formData.working_parts} onChange={e => setFormData({ ...formData, working_parts: e.target.value })} />
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700">Description</label>
                    <textarea required className="w-full border p-2 rounded h-24" placeholder="Detailed description of the item..."
                        value={formData.description} onChange={e => setFormData({ ...formData, description: e.target.value })} />
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700">Price ($)</label>
                        <input type="number" step="0.01" required className="w-full border p-2 rounded" placeholder="0.00"
                            value={formData.price} onChange={e => setFormData({ ...formData, price: e.target.value })} />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700">Location</label>
                        <input type="text" required className="w-full border p-2 rounded" placeholder="City, State"
                            value={formData.location} onChange={e => setFormData({ ...formData, location: e.target.value })} />
                    </div>
                </div>

                <div className="pt-4">
                    <button type="submit" className="w-full bg-primary text-white py-3 rounded-md hover:bg-blue-600 font-bold">
                        Post Listing
                    </button>
                    <button type="button" onClick={() => setPage('home')} className="w-full mt-2 text-gray-600 py-2 hover:bg-gray-50 rounded">
                        Cancel
                    </button>
                </div>
            </form>
        </div>
    );
};

const DashboardPage = () => {
    const { user } = useAuth();
    const [myListings, setMyListings] = useState([]);
    const [sentRequests, setSentRequests] = useState([]);
    const [incomingRequests, setIncomingRequests] = useState([]);

    useEffect(() => {
        if (user) loadDashboardData();
    }, [user]);

    const loadDashboardData = async () => {
        try {
            // In a real app we'd have a specific endpoint for my listings
            // Using logic: fetch all and filter by seller_id (not efficient but works for now)
            // Or use an endpoint if we made one. We haven't made a specific "my-listings" endpoint, 
            // but we can add one or just use correct endpoint. 
            // Actually, we should probably add one, but for now let's just use the requests endpoints which we DID make on "my-requests" and "incoming".

            // Note: listings router has generic filter, but getting "my" listings specifically might need a query param or separate endpoint.
            // Let's leave listings empty for now or try to fetch generic and filter client side (bad practice but works for demo).
            // Better: update backend to support "seller_id" filter.

            const reqSent = await api.get('/requests/my-requests');
            setSentRequests(reqSent.data);

            const reqInc = await api.get('/requests/incoming');
            setIncomingRequests(reqInc.data);

            // Hack for listings:
            const listRes = await api.get('/listings/?limit=100');
            setMyListings(listRes.data.filter(l => l.seller_id === user.id));

        } catch (err) {
            console.error(err);
        }
    };

    const handleUpdateStatus = async (reqId, status) => {
        try {
            if (status === 'accept') await api.put(`/requests/${reqId}/accept`);
            if (status === 'reject') await api.put(`/requests/${reqId}/reject`);
            loadDashboardData();
        } catch (err) {
            alert("Action failed");
        }
    };

    return (
        <div className="max-w-7xl mx-auto px-4 py-8">
            <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* Incoming Requests (As Seller) */}
                <div className="glass-panel p-6 rounded-2xl shadow-sm border border-slate-200">
                    <h2 className="text-xl font-bold mb-4 text-slate-800 flex items-center">
                        <span className="mr-2">📥</span> Incoming Buy Requests
                    </h2>
                    {incomingRequests.length === 0 ? (
                        <p className="text-slate-500 italic">No incoming requests yet.</p>
                    ) : (
                        <div className="space-y-4">
                            {incomingRequests.map(req => (
                                <div key={req.id} className="bg-white p-5 rounded-xl border border-slate-100 shadow-sm hover:shadow-md transition-all">
                                    <div className="flex justify-between items-start mb-3">
                                        <div className="flex items-center space-x-2">
                                            <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold text-lg">
                                                {req.buyer_name ? req.buyer_name[0].toUpperCase() : 'B'}
                                            </div>
                                            <div>
                                                <p className="font-bold text-slate-800">{req.buyer_name}</p>
                                                <p className="text-xs text-slate-500">{req.buyer_location}</p>
                                            </div>
                                        </div>
                                        <span className={`px-2 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${req.status === 'pending' ? 'bg-amber-100 text-amber-700' : req.status === 'accepted' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                                            {req.status}
                                        </span>
                                    </div>

                                    <div className="bg-slate-50 p-3 rounded-lg text-sm text-slate-600 mb-4">
                                        <p>Wants to buy your listing <span className="font-semibold text-primary">#{req.listing_id}</span></p>
                                        <p className="text-xs text-slate-400 mt-1">{new Date(req.created_at).toLocaleDateString()}</p>
                                    </div>

                                    {/* Contact Actions */}
                                    <div className="flex flex-col space-y-2">
                                        {req.buyer_phone && (
                                            <a href={`https://wa.me/${req.buyer_phone.replace(/\D/g, '')}`} target="_blank" className="flex items-center justify-center space-x-2 w-full bg-[#25D366] text-white py-2 rounded-lg hover:bg-[#128C7E] font-medium transition-colors">
                                                <span>💬</span> <span>Chat on WhatsApp</span>
                                            </a>
                                        )}
                                        <div className="flex space-x-2">
                                            <a href={`mailto:${req.buyer_email}`} className="flex-1 flex items-center justify-center space-x-1 bg-slate-100 text-slate-700 py-2 rounded-lg hover:bg-slate-200 text-sm font-medium transition-colors">
                                                <span>✉️</span> <span>Email</span>
                                            </a>
                                            {req.buyer_phone && (
                                                <a href={`tel:${req.buyer_phone}`} className="flex-1 flex items-center justify-center space-x-1 bg-slate-100 text-slate-700 py-2 rounded-lg hover:bg-slate-200 text-sm font-medium transition-colors">
                                                    <span>📞</span> <span>Call</span>
                                                </a>
                                            )}
                                        </div>
                                    </div>

                                    {req.status === 'pending' && (
                                        <div className="mt-4 pt-3 border-t border-slate-100 flex space-x-3">
                                            <button onClick={() => handleUpdateStatus(req.id, 'accept')} className="flex-1 bg-green-500 text-white py-2 rounded-lg hover:bg-green-600 font-medium text-sm">Accept</button>
                                            <button onClick={() => handleUpdateStatus(req.id, 'reject')} className="flex-1 bg-red-100 text-red-600 py-2 rounded-lg hover:bg-red-200 font-medium text-sm">Reject</button>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Sent Requests (As Buyer) */}
                <div className="glass-panel p-6 rounded-2xl shadow-sm border border-slate-200">
                    <h2 className="text-xl font-bold mb-4 text-slate-800 flex items-center">
                        <span className="mr-2">📤</span> My Sent Requests
                    </h2>
                    {sentRequests.length === 0 ? (
                        <p className="text-slate-500 italic">You haven't made any requests.</p>
                    ) : (
                        <div className="space-y-4">
                            {sentRequests.map(req => (
                                <div key={req.id} className="bg-white p-4 rounded-xl border border-slate-100 flex justify-between items-center hover:shadow-sm">
                                    <div>
                                        <span className="font-bold text-slate-700">Listing #{req.listing_id}</span>
                                        <p className="text-xs text-slate-400">{new Date(req.created_at).toLocaleDateString()}</p>
                                    </div>
                                    <span className={`px-2 py-1 rounded-full text-xs font-bold uppercase ${req.status === 'pending' ? 'bg-amber-100 text-amber-700' : req.status === 'accepted' ? 'bg-green-100 text-green-700' : 'bg-slate-100'}`}>
                                        {req.status}
                                    </span>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* My Listings */}
            <div className="mt-8 glass-panel p-6 rounded-2xl shadow-sm border border-slate-200">
                <h2 className="text-xl font-bold mb-6 text-slate-800">📦 My Listings</h2>
                {myListings.length === 0 ? (
                    <p className="text-gray-500">No listings active.</p>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {myListings.map(l => (
                            <div key={l.id} className="border p-4 rounded-md">
                                <h3 className="font-medium">{l.title}</h3>
                                <div className="flex justify-between mt-2 text-sm text-gray-600">
                                    <span>${l.price}</span>
                                    <span>{l.status}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

// --- App Container ---

const App = () => {
    const [page, setPage] = useState('home');

    return (
        <AuthProvider>
            <div className="min-h-screen bg-gray-50 text-gray-900 font-sans">
                <Navbar setPage={setPage} />
                <main>
                    {page === 'home' && <HomePage setPage={setPage} />}
                    {page === 'login' && <LoginPage setPage={setPage} />}
                    {page === 'register' && <RegisterPage setPage={setPage} />}
                    {page === 'create-listing' && <CreateListingPage setPage={setPage} />}
                    {page === 'dashboard' && <DashboardPage />}
                </main>
            </div>
        </AuthProvider>
    );
};

// Render
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
