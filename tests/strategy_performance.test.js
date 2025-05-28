const { fetchData } = require('../static/strategy_performance');

test('fetchData should return data from the API', async () => {
    const mockResponse = { data: [1, 2, 3] };
    global.fetch = jest.fn(() =>
        Promise.resolve({
            json: () => Promise.resolve(mockResponse),
        })
    );

    const data = await fetchData();
    expect(data).toEqual(mockResponse);
    expect(global.fetch).toHaveBeenCalledWith('/api/data');
});
