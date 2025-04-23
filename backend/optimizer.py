# backend/optimizer.py

class TrafficOptimizer:
    def __init__(self):
        # Minimum green per lane is now 15 seconds, total cycle 180 seconds
        self.min_green = 5
        self.max_green = 60
        self.emergency_priority = 0.7

    def compute_green_time(self, data: dict) -> dict:
        total = self.max_green
        # First, check for any emergency vehicles
        em_lanes = [l for l, v in data.items() if v['emergency']]
        if em_lanes:
            p = em_lanes[0]
            # allocate up to emergency_priority * total, but leave at least min_green for others
            green_p = min(
                int(self.emergency_priority * total),
                total - self.min_green * (len(data) - 1)
            )
            times = {p: green_p}
            rem = total - green_p
            for l in data:
                if l != p:
                    times[l] = max(self.min_green, rem // (len(data) - 1))
            return times

        # No emergency: distribute based on counts
        tot_veh = sum(v['count'] for v in data.values())
        if tot_veh == 0:
            # even if no vehicles, give each at least min_green
            base = total // len(data)
            return {l: max(self.min_green, base) for l in data}

        # proportional allocation, then adjust to respect min_green
        times = {
            l: max(self.min_green, int(v['count'] / tot_veh * total))
            for l, v in data.items()
        }
        diff = total - sum(times.values())
        # tweak one second at a time until we hit exactly total
        while diff != 0:
            adj = 1 if diff > 0 else -1
            # add to the smallest when increasing, subtract from largest when decreasing
            key = min(times, key=times.get) if diff > 0 else max(times, key=times.get)
            if times[key] + adj >= self.min_green:
                times[key] += adj
                diff -= adj
        return times


optimizer = TrafficOptimizer()
