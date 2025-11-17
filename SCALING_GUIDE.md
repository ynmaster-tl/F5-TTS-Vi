# RunPod Scaling Guide

## 🚀 Worker Scaling Strategy

### Quick Reference

| Max Workers | Capacity | Use Case | Estimated Cost/Hour* |
|-------------|----------|----------|---------------------|
| 0-3 | 1-18 jobs | Testing, MVP, startup | $0 - $1.32 |
| 3-10 | 18-60 jobs | Growing app, SMB | $1.32 - $4.40 |
| 10-30 | 60-180 jobs | Medium production | $4.40 - $13.20 |
| 30-50 | 180-300 jobs | Large production | $13.20 - $22.00 |
| 50-100 | 300-600 jobs | High scale | $22.00 - $44.00 |
| 100+ | 600+ jobs | Enterprise | $44.00+ |

*Based on RTX 3090 at ~$0.44/hour per worker (prices vary by GPU type)

### How Auto-Scaling Works

Your orchestrator automatically scales RunPod workers based on queue size:

```typescript
// Logic in queueManager.ts
if (processing >= 1 && pending > 1) workersNeeded = 1
if (processing >= 2 && pending > 2) workersNeeded = 2
if (processing >= 3 && pending > 3) workersNeeded = 3
// ... continues based on demand
```

**Key Points:**
- ✅ Workers spin up automatically when jobs queue
- ✅ Workers spin down to Min (0) when idle
- ✅ No manual intervention needed
- ✅ You only pay for active worker time

### Setting Max Workers

#### In RunPod Console:
1. Go to Endpoint → Settings
2. Set **Min Workers**: 0 (save costs when idle)
3. Set **Max Workers**: Your desired limit
4. Click Save

#### Recommended Settings:

**Testing/Development:**
```
Min: 0, Max: 3
- Low cost
- Good for testing
- Handles ~18 concurrent jobs
```

**Small Production (< 1000 users):**
```
Min: 0, Max: 10
- Moderate cost
- Handles ~60 concurrent jobs
- Good for growing apps
```

**Medium Production (1000-10000 users):**
```
Min: 1, Max: 30
- Always 1 worker ready (faster first response)
- Handles ~180 concurrent jobs
- Predictable performance
```

**Large Production (10000+ users):**
```
Min: 3, Max: 50+
- Always workers ready
- Handles 300+ concurrent jobs
- High availability
```

**Enterprise:**
```
Min: 10, Max: 100+
- Maximum throughput
- Consider multiple endpoints for redundancy
- May need to contact RunPod for high limits
```

### Cost Optimization Tips

1. **Use Min Workers = 0** for variable traffic
   - Workers auto-scale when needed
   - Zero cost when idle
   - ~30s cold start time

2. **Set Min Workers > 0** for consistent traffic
   - Faster response (no cold start)
   - Predictable performance
   - Trade-off: always-on cost

3. **Monitor and Adjust**
   - Check endpoint metrics in RunPod console
   - Look at queue depth and worker utilization
   - Adjust Max Workers based on actual usage

4. **Use Local GPU First**
   - Your orchestrator prioritizes local GPU (free)
   - RunPod only scales when local is busy
   - Reduces cloud costs significantly

### Advanced Scaling Strategies

#### Multi-Region Deployment
For global users:
- Create endpoints in different regions (US, EU, Asia)
- Route jobs based on user location
- Better latency and redundancy

#### GPU Type Selection
Different GPUs for different needs:

| GPU | VRAM | Speed | Cost | Best For |
|-----|------|-------|------|----------|
| RTX 3090 | 24GB | Fast | ~$0.44/h | General use, best value |
| RTX 4090 | 24GB | Faster | ~$0.69/h | High throughput needed |
| A40 | 48GB | Fast | ~$0.79/h | Large batches |
| A100 | 80GB | Fastest | ~$1.99/h | Maximum performance |

#### Load Balancing
For 100+ workers:
- Consider using RunPod Load Balancing endpoints
- More complex but better control
- Custom routing logic possible

### Monitoring Worker Performance

#### Key Metrics to Watch:
1. **Queue Depth** - How many jobs waiting?
2. **Worker Utilization** - Are workers idle or busy?
3. **Response Time** - How fast are jobs completing?
4. **Error Rate** - Any workers crashing?

#### In RunPod Console:
- Navigate to Endpoint → Analytics
- Check "Workers" and "Jobs" graphs
- Adjust Max Workers if queue consistently high

#### In Your Application:
```bash
# Check endpoint health
curl https://api.runpod.ai/v2/$ENDPOINT_ID/health \
  -H "Authorization: Bearer $RUNPOD_API_KEY"

# Response shows:
{
  "jobs": {
    "completed": 150,
    "failed": 2,
    "inProgress": 3,
    "inQueue": 12,  # <-- Watch this number
    "retried": 1
  },
  "workers": {
    "idle": 2,      # <-- Workers ready
    "running": 5    # <-- Workers busy
  }
}
```

### Troubleshooting Scale Issues

**Problem: Workers not scaling up**
- Check Max Workers setting
- Verify endpoint is active
- Check RunPod account limits
- Contact RunPod support for limit increase

**Problem: High costs**
- Set Max Workers lower
- Increase local GPU usage first
- Consider cheaper GPU types
- Set Min Workers to 0

**Problem: Slow response times**
- Increase Max Workers
- Set Min Workers > 0 to avoid cold starts
- Check if jobs are timing out
- Consider faster GPU types

**Problem: Workers idle but jobs queued**
- Check execution timeout settings
- Verify workers aren't crashing
- Check endpoint logs
- May need to restart endpoint

### FAQ

**Q: What happens if I hit Max Workers?**
A: New jobs queue until workers become available. No jobs are lost.

**Q: Can I change Max Workers anytime?**
A: Yes! Change in RunPod console, takes effect immediately.

**Q: Do I pay for idle workers?**
A: Only if Min Workers > 0. Set Min to 0 to pay only when processing.

**Q: How fast do workers scale?**
A: ~30-60 seconds for cold start. Warm workers respond instantly.

**Q: Is there a hard limit on Max Workers?**
A: RunPod may have account limits. Contact support for high limits (100+).

**Q: Should I use one endpoint or multiple?**
A: One endpoint is fine for most cases. Use multiple for:
- Different regions
- Different models
- Redundancy/failover

### Summary

**Start Small:**
- Begin with Max 3 workers
- Monitor usage for 1-2 weeks
- Adjust based on actual demand

**Scale Gradually:**
- Increase Max Workers as traffic grows
- Keep Min Workers = 0 unless needed
- Monitor costs and adjust

**Optimize:**
- Use local GPU first (free)
- Choose right GPU type for your needs
- Set Max Workers based on peak load + buffer

**No Limits:**
The codebase supports unlimited workers. The only limit is:
1. Your RunPod account settings
2. Your budget
3. RunPod's infrastructure capacity

Scale as big as you need! 🚀
