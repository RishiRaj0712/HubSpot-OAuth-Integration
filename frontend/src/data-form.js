import { useState } from 'react';
import {
    Box,
    Typography,
    Button,
    CircularProgress,
} from '@mui/material';
import axios from 'axios';

const endpointMapping = {
    'Notion': 'notion',
    'Airtable': 'airtable',
    'HubSpot': 'hubspot',
};

export const DataForm = ({ integrationType, credentials }) => {
    const [loadedData, setLoadedData] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const endpoint = endpointMapping[integrationType];

    const handleLoad = async () => {
        try {
            setIsLoading(true);
            const formData = new FormData();
            formData.append('credentials', JSON.stringify(credentials));
            const response = await axios.post(`http://localhost:8000/integrations/${endpoint}/load`, formData);
            const data = response.data;
            console.log("Loaded Data: ",data);
            setLoadedData(data);
            setIsLoading(false);
        } catch (e) {
            setIsLoading(false);
            alert(e?.response?.data?.detail);
        }
    }

    return (
        <Box display='flex' justifyContent='center' alignItems='center' flexDirection='column' width='100%'>
            <Box display='flex' flexDirection='column' width='100%'>
                <Button
                    onClick={handleLoad}
                    sx={{mt: 2}}
                    variant='contained'
                    disabled={isLoading}
                >
                    {isLoading ? <CircularProgress size={20} /> : 'Load Data'}
                </Button>
                <Button
                    onClick={() => setLoadedData([])}
                    sx={{mt: 1}}
                    variant='contained'
                >
                    Clear Data
                </Button>

                {loadedData.length > 0 && (
                    <Box sx={{ mt: 2 }}>
                        <Typography variant="h6">Loaded Data:</Typography>
                        {loadedData.map((item, index) => (
                            <Box key={index} sx={{ mt: 1, p: 2, border: '1px solid #ddd', borderRadius: '4px' }}>
                                <Typography variant="body1"><strong>Name:</strong> {item.name}</Typography>
                                <Typography variant="body2"><strong>ID:</strong> {item.id}</Typography>
                                <Typography variant="body2"><strong>Type:</strong> {item.type}</Typography>
                                <Typography variant="body2"><strong>Created At:</strong> {new Date(item.creation_time).toLocaleString()}</Typography>
                                <Typography variant="body2"><strong>Last Modified:</strong> {new Date(item.last_modified_time).toLocaleString()}</Typography>
                            </Box>
                        ))}
                    </Box>
                )}
            </Box>
        </Box>
    );
}
